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

from apps.bible.models import Speaker, VerseSpeakerMapping

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
            mappings = self._build_mappings(data, name_to_id)
            VerseSpeakerMapping.objects.bulk_create(mappings, batch_size=BATCH_SIZE)

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
        mappings = []
        for entry in data:
            speakers = entry.get("speaker") or []
            if not speakers:
                continue
            vid = entry["id"]
            try:
                version, book, chapter, verse = vid.split(":")
            except ValueError as exc:
                raise CommandError(
                    f"Malformed verse id {vid!r}; expected version:book:chapter:verse"
                ) from exc
            chapter = int(chapter)
            verse = int(verse)
            for sp in speakers:
                if not sp:
                    continue
                mappings.append(
                    VerseSpeakerMapping(
                        speaker_id=name_to_id[sp],
                        version=version,
                        book=book,
                        chapter=chapter,
                        verse=verse,
                    )
                )
        return mappings
