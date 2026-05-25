"""Import speaker.json into the Speaker / VerseSpeakerMapping tables.

Idempotent: re-running replaces all rows so the DB reflects the current
speaker.json. Not a migration because speaker.json gets edited and
regenerated regularly (via `bible_extract_speakers` plus manual overrides).
"""

import json
from pathlib import Path

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.bible.models import Speaker, Verse, VerseSpeakerMapping

DATA_DIR = Path(apps.get_app_config("bible").path) / "data"
DEFAULT_SPEAKER_PATH = DATA_DIR / "speaker.json"

BATCH_SIZE = 1000


class Command(BaseCommand):
    """Populate Speaker and VerseSpeakerMapping from speaker.json."""

    help = "Import speaker.json into the Speaker / VerseSpeakerMapping tables."

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            default=str(DEFAULT_SPEAKER_PATH),
            help="Path to the speaker.json file.",
        )

    def handle(self, *args, **options):
        path = Path(options["path"])
        data = self._load_speaker_file(path)

        # Collect every unique speaker name across the file.
        unique_names = set()
        for entry in data:
            for sp in entry.get("speaker", []) or []:
                if sp:
                    unique_names.add(sp)

        with transaction.atomic():
            name_to_id = self._upsert_speakers(unique_names)
            # Rebuild the mapping table from scratch — speaker.json is the
            # source of truth and changes are diff-y, not append-only.
            VerseSpeakerMapping.objects.all().delete()
            mappings, skipped = self._build_mappings(data, name_to_id)
            VerseSpeakerMapping.objects.bulk_create(mappings, batch_size=BATCH_SIZE)

        if skipped:
            self.stdout.write(
                self.style.WARNING(
                    f"Skipped {len(skipped)} entries with no matching Verse "
                    "(run `verses_to_db` first): "
                    f"{skipped[:5]!r}{'…' if len(skipped) > 5 else ''}"
                )
            )
        self.stdout.write(
            self.style.SUCCESS(
                f"Speakers loaded: {len(name_to_id)} unique speakers, "
                f"{len(mappings)} verse mappings."
            )
        )

    @staticmethod
    def _load_speaker_file(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError as exc:
            raise CommandError(f"Speaker file not found: {path}") from exc
        except json.JSONDecodeError as exc:
            raise CommandError(f"Invalid JSON in {path}: {exc}") from exc
        if not isinstance(data, list):
            raise CommandError("Expected a JSON array at the top level.")
        return data

    @staticmethod
    def _upsert_speakers(unique_names):
        existing = {s.name: s.id for s in Speaker.objects.all()}
        new_names = [n for n in unique_names if n not in existing]
        if new_names:
            Speaker.objects.bulk_create(
                [Speaker(name=n) for n in new_names],
                batch_size=BATCH_SIZE,
            )
        return {s.name: s.id for s in Speaker.objects.all()}

    @staticmethod
    def _build_mappings(data, name_to_id):
        # Verse rows are populated by `verses_to_db` from bible.json; entries
        # in speaker.json that reference a non-existent verse are skipped so
        # the import doesn't fail on a single stray id. Returns (mappings,
        # skipped_verse_ids).
        known_verse_ids = set(
            Verse.objects.filter(
                pk_id__in=[e["id"] for e in data if "id" in e]
            ).values_list("pk_id", flat=True)
        )
        mappings = []
        skipped = []
        for entry in data:
            speakers = entry.get("speaker") or []
            if not speakers:
                continue
            vid = entry["id"]
            if vid not in known_verse_ids:
                skipped.append(vid)
                continue
            for sp in speakers:
                if not sp:
                    continue
                mappings.append(
                    VerseSpeakerMapping(
                        speaker_id=name_to_id[sp],
                        verse_id=vid,
                    )
                )
        return mappings, skipped
