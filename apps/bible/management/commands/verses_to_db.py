"""Populate the Verse table from apps/bible/data/bible.json.

Idempotent: re-running upserts every verse so the DB reflects the current
bible.json (text edits get refreshed). The admin browses this table to attach
SpeakerOverrides; existing overrides survive re-runs because they FK to the
verse PK, which is stable.
"""

import json
from pathlib import Path

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.bible.models import Verse

DATA_DIR = Path(apps.get_app_config("bible").path) / "data"
DEFAULT_INPUT = DATA_DIR / "bible.json"

BATCH_SIZE = 1000


class Command(BaseCommand):
    """Upsert Verse rows from bible.json."""

    help = "Populate the Verse table from bible.json (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--input",
            default=str(DEFAULT_INPUT),
            help="Path to the bible.json file.",
        )

    def handle(self, *args, **options):
        path = Path(options["input"])
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError as exc:
            raise CommandError(f"Bible file not found: {path}") from exc
        except json.JSONDecodeError as exc:
            raise CommandError(f"Invalid JSON in {path}: {exc}") from exc
        if not isinstance(data, list):
            raise CommandError("Expected a JSON array at the top level.")

        verses = []
        for sort_order, entry in enumerate(data):
            vid = entry.get("id")
            text = entry.get("_text_", "")
            if not vid:
                continue
            try:
                version, book, chapter, verse = vid.split(":")
            except ValueError as exc:
                raise CommandError(
                    f"Malformed verse id {vid!r}; expected version:book:chapter:verse"
                ) from exc
            verses.append(
                Verse(
                    pk_id=vid,
                    version=version,
                    book=book,
                    chapter=int(chapter),
                    verse=int(verse),
                    text=text,
                    sort_order=sort_order,
                )
            )

        with transaction.atomic():
            Verse.objects.bulk_create(
                verses,
                batch_size=BATCH_SIZE,
                update_conflicts=True,
                unique_fields=["pk_id"],
                update_fields=["version", "book", "chapter", "verse", "text", "sort_order"],
            )

        self.stdout.write(
            self.style.SUCCESS(f"Upserted {len(verses)} verses from {path}.")
        )
