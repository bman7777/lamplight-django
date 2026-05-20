"""Import Strong's concordance JSON into the ConcordanceEntry table."""

import json
from pathlib import Path

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.bible.models import ConcordanceEntry

DATA_DIR = Path(apps.get_app_config("bible").path) / "data"
DEFAULT_CONCORDANCE_PATH = DATA_DIR / "concordance.json"

BATCH_SIZE = 1000


class Command(BaseCommand):
    """Management command that loads concordance.json into the database."""

    help = "Import Strong's concordance JSON into the ConcordanceEntry table."

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            default=str(DEFAULT_CONCORDANCE_PATH),
            help="Path to the concordance JSON file.",
        )

    def handle(self, *args, **options):
        path = Path(options["path"])
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError as exc:
            raise CommandError(f"Concordance file not found: {path}") from exc
        except json.JSONDecodeError as exc:
            raise CommandError(f"Invalid JSON in {path}: {exc}") from exc

        if not isinstance(data, list):
            raise CommandError("Expected a JSON array at the top level.")

        entries = [
            ConcordanceEntry(
                concord_id=item["concord_id"],
                original_word=item.get("original_word", ""),
                transliteration=item.get("transliteration", ""),
                part_of_speech=item.get("part_of_speech", ""),
                english_translations=item.get("english_translations", []),
                outline_definitions=item.get("outline_definitions", []),
                strongs_definition=item.get("strongs_definition", []),
            )
            for item in data
        ]

        with transaction.atomic():
            ConcordanceEntry.objects.bulk_create(
                entries,
                batch_size=BATCH_SIZE,
                update_conflicts=True,
                unique_fields=["concord_id"],
                update_fields=[
                    "original_word",
                    "transliteration",
                    "part_of_speech",
                    "english_translations",
                    "outline_definitions",
                    "strongs_definition",
                ],
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Concordance import complete. Upserted {len(entries)} entries."
            )
        )
