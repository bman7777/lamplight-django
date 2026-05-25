"""Seed SpeakerOverride rows from apps/bible/data/speaker_overrides.json.

One-time bootstrap so the DB inherits the legacy JSON-tracked overrides. After
this runs, the DB (edited via the Django admin) is the sole source of truth and
`bible_extract_speakers` reads overrides directly from it — this command and
speaker_overrides.json are slated for removal once every environment is seeded.

WARNING: not safe to re-run casually. It deletes all SpeakerOverride rows and
rebuilds them from the JSON, so running it against a DB that already has admin
edits not reflected in the JSON will discard those edits. Speakers missing from
the Speaker table are created on the fly.
"""

import json
from pathlib import Path

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.bible.models import Speaker, SpeakerOverride, Verse

DATA_DIR = Path(apps.get_app_config("bible").path) / "data"
DEFAULT_PATH = DATA_DIR / "speaker_overrides.json"


class Command(BaseCommand):
    """Import speaker_overrides.json into SpeakerOverride rows."""

    help = "Import speaker_overrides.json into the SpeakerOverride table."

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            default=str(DEFAULT_PATH),
            help="Path to the speaker_overrides.json file.",
        )

    def handle(self, *args, **options):
        path = Path(options["path"])
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError as exc:
            raise CommandError(f"Overrides file not found: {path}") from exc
        except json.JSONDecodeError as exc:
            raise CommandError(f"Invalid JSON in {path}: {exc}") from exc
        if not isinstance(data, list):
            raise CommandError("Expected a JSON array at the top level.")

        unique_names = {sp for e in data for sp in (e.get("speaker") or []) if sp}

        with transaction.atomic():
            name_to_id = self._upsert_speakers(unique_names)
            # Full rebuild — this is a one-time seed of the DB from the JSON.
            SpeakerOverride.objects.all().delete()
            missing_verses = self._create_overrides(data, name_to_id)

        msg = f"Imported {len(data) - len(missing_verses)} overrides from {path}."
        if missing_verses:
            self.stdout.write(
                self.style.WARNING(
                    f"Skipped {len(missing_verses)} entries with no matching Verse "
                    "(run `verses_to_db` first if these should exist): "
                    f"{missing_verses[:5]!r}{'…' if len(missing_verses) > 5 else ''}"
                )
            )
        self.stdout.write(self.style.SUCCESS(msg))

    @staticmethod
    def _upsert_speakers(unique_names):
        existing = {s.name: s.id for s in Speaker.objects.all()}
        new_names = [n for n in unique_names if n not in existing]
        if new_names:
            Speaker.objects.bulk_create([Speaker(name=n) for n in new_names])
        return {s.name: s.id for s in Speaker.objects.all()}

    @staticmethod
    def _create_overrides(data, name_to_id):
        known_verse_ids = set(
            Verse.objects.filter(
                pk_id__in=[e["id"] for e in data if "id" in e]
            ).values_list("pk_id", flat=True)
        )
        missing = []
        overrides = []
        m2m_rows = []
        for entry in data:
            vid = entry.get("id")
            speakers = entry.get("speaker") or []
            if not vid:
                continue
            if vid not in known_verse_ids:
                missing.append(vid)
                continue
            overrides.append(SpeakerOverride(verse_id=vid))
            for sp in speakers:
                if sp:
                    m2m_rows.append((vid, name_to_id[sp]))

        SpeakerOverride.objects.bulk_create(overrides)
        through = SpeakerOverride.speakers.through
        through.objects.bulk_create(
            [
                through(speakeroverride_id=vid, speaker_id=sid)
                for vid, sid in m2m_rows
            ]
        )
        return missing
