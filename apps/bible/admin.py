"""Bible admin: browse every verse and edit its SpeakerOverride.

SpeakerOverride is what supersedes the extractor's guesses in speaker.json.
The DB is the source of truth — re-run `bible_extract_speakers` (which reads
SpeakerOverride rows directly) and `speakers_to_db` to push edits through to
the search results.

The Verse changelist is editable in place: every row on the page carries a
searchable speaker picker, and one Save button writes overrides for every row
you touched (filters/search/pagination still work via the stock changelist).
Clicking into a verse and using the inline still works too.
"""

from django import forms
from django.contrib import admin, messages
from django.contrib.admin.widgets import AutocompleteSelectMultiple
from django.http import HttpResponseRedirect

from .models import Speaker, SpeakerOverride, Verse


class OverrideSpeakersForm(forms.Form):
    """One verse row's speaker picker on the editable changelist.

    Bound per verse with prefix ``spk-<verse pk>`` so each row's data is
    isolated. Pre-filled with the verse's effective speakers (override if any,
    else the extracted speakers). ``speakers`` is optional: selecting exactly
    the extracted speakers — or clearing the row — removes any override.
    """

    speakers = forms.ModelMultipleChoiceField(
        queryset=Speaker.objects.all(),
        required=False,
        widget=AutocompleteSelectMultiple(
            SpeakerOverride._meta.get_field("speakers"),
            admin.site,
        ),
    )


class HasOverrideFilter(admin.SimpleListFilter):
    """Filter verses by whether they have a non-empty SpeakerOverride."""

    title = "has override"
    parameter_name = "has_override"

    def lookups(self, request, model_admin):
        return [("yes", "Yes"), ("no", "No")]

    def queryset(self, request, qs):
        if self.value() == "yes":
            return qs.filter(speaker_override__speakers__isnull=False).distinct()
        if self.value() == "no":
            return qs.exclude(speaker_override__speakers__isnull=False).distinct()
        return qs


class SpeakerOverrideInline(admin.StackedInline):
    """Edit the override speakers on the Verse change page."""

    model = SpeakerOverride
    extra = 1
    max_num = 1
    can_delete = True
    autocomplete_fields = ("speakers",)
    verbose_name = "Speaker override"
    verbose_name_plural = "Speaker override"


@admin.register(Verse)
class VerseAdmin(admin.ModelAdmin):
    """Changelist that browses every verse and edits its override speakers.

    The changelist is rendered by a custom template that replaces the result
    table with one ``OverrideSpeakersForm`` per row; ``changelist_view`` below
    binds those forms and persists the changed ones on Save.
    """

    change_list_template = "admin/bible/verse/change_list.html"
    list_display = ("reference", "verse_text", "override_speakers")
    list_filter = (HasOverrideFilter, "book", "version")
    search_fields = ("pk_id", "text")
    inlines = [SpeakerOverrideInline]
    list_per_page = 50
    readonly_fields = ("pk_id", "version", "book", "chapter", "verse", "text", "sort_order")
    fieldsets = (
        (
            None,
            {
                "fields": (
                    ("book", "chapter", "verse"),
                    "version",
                    "text",
                    "pk_id",
                ),
            },
        ),
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .prefetch_related("speaker_override__speakers", "speaker_mappings__speaker")
        )

    @staticmethod
    def _mapped_speaker_ids(verse):
        """PKs of the verse's extracted speakers (VerseSpeakerMapping)."""
        return sorted(m.speaker_id for m in verse.speaker_mappings.all())

    @staticmethod
    def _override_speaker_ids(verse):
        """PKs of the verse's override speakers, or None if no override row."""
        override = getattr(verse, "speaker_override", None)
        if override is None:
            return None
        return sorted(speaker.pk for speaker in override.speakers.all())

    @classmethod
    def _effective_speaker_ids(cls, verse):
        """Speakers to show for a verse, and whether they come from an override.

        A non-empty override wins; otherwise we fall back to the extracted
        speakers. An empty override row is treated as "no override" (matching
        how `bible_extract_speakers` reads them), so it also falls back.
        """
        override_ids = cls._override_speaker_ids(verse)
        if override_ids:
            return override_ids, True
        return cls._mapped_speaker_ids(verse), False

    @staticmethod
    def _row_prefix(verse):
        """Form prefix / marker namespace for a verse's changelist row.

        The template builds a hidden ``<prefix>-present`` input with this same
        scheme (see change_list.html); keep the two in sync.
        """
        return f"spk-{verse.pk}"

    def changelist_view(self, request, extra_context=None):
        """Render the page, then bind a speaker picker to each verse row.

        Each picker is pre-filled with the verse's effective speakers — the
        override if one exists, else the extracted speakers. On Save (the
        ``_save_speakers`` button) a row only writes an override when its
        selection differs from the extracted set; selecting exactly the
        extracted speakers (or clearing the row) removes any override so the
        verse falls back to extraction. We let the stock changelist build the
        (filtered, searched, paginated) page, then attach our forms to it.
        """
        response = super().changelist_view(request, extra_context)
        # Redirects (bad filters, etc.) have no context to enrich.
        if not hasattr(response, "context_data"):
            return response
        change_list = response.context_data.get("cl")
        if change_list is None:
            return response

        verses = list(change_list.result_list)
        saving = request.method == "POST" and "_save_speakers" in request.POST

        rows = []  # (verse, form, is_override, has_curly_quote) in page order
        for verse in verses:
            effective_ids, is_override = self._effective_speaker_ids(verse)
            initial = {"speakers": effective_ids}
            prefix = self._row_prefix(verse)
            form = (
                OverrideSpeakersForm(request.POST, prefix=prefix, initial=initial)
                if saving
                else OverrideSpeakersForm(prefix=prefix, initial=initial)
            )
            # Curly double quotes (U+201C/U+201D), not straight ASCII ".
            has_curly_quote = "“" in verse.text or "”" in verse.text
            rows.append((verse, form, is_override, has_curly_quote))

        if saving and all(form.is_valid() for _, form, _, _ in rows):
            changed = 0
            for verse, form, _, _ in rows:
                # Only touch rows that were actually on the submitted form. An
                # empty multi-select submits no field at all, so the hidden
                # "-present" marker is what tells an intentional clear apart
                # from a row that wasn't rendered (e.g. the page shifted since
                # render) — without it, such a row would look "cleared" and we
                # would wrongly delete its override.
                if f"{self._row_prefix(verse)}-present" not in request.POST:
                    continue
                if not form.has_changed():
                    continue
                selected = {s.pk for s in form.cleaned_data["speakers"]}
                mapped = set(self._mapped_speaker_ids(verse))
                if selected and selected != mapped:
                    override, _created = SpeakerOverride.objects.get_or_create(verse=verse)
                    override.speakers.set(selected)
                else:
                    # Matches extraction (or empty): no override needed.
                    SpeakerOverride.objects.filter(verse=verse).delete()
                changed += 1
            if changed:
                self.message_user(
                    request,
                    f"Updated speakers on {changed} verse(s).",
                    messages.SUCCESS,
                )
            else:
                self.message_user(
                    request, "No speaker changes to save.", messages.INFO
                )
            # POST/redirect/GET: bounce back to the same filtered page.
            return HttpResponseRedirect(request.get_full_path())

        response.context_data["speaker_rows"] = rows
        response.context_data["speaker_media"] = OverrideSpeakersForm().media
        return response

    @admin.display(description="Reference", ordering="sort_order")
    def reference(self, obj):
        return f"{obj.book} {obj.chapter}:{obj.verse}"

    @admin.display(description="Verse")
    def verse_text(self, obj):
        return obj.text

    @admin.display(description="Override speakers")
    def override_speakers(self, obj):
        ov = getattr(obj, "speaker_override", None)
        if ov is None:
            return "—"
        names = sorted(s.name for s in ov.speakers.all())
        return ", ".join(names) if names else "—"


@admin.register(Speaker)
class SpeakerAdmin(admin.ModelAdmin):
    """Registered so the inline's autocomplete_fields can resolve Speakers."""

    list_display = ("name",)
    search_fields = ("name",)
    ordering = ("name",)
