"""Seed the haystack (Whoosh) index from apps/bible/data/bible.json."""

import json
from pathlib import Path

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from haystack import connections

from apps.bible.models import Verse
from apps.bible.search_indexes import VerseIndex

DATA_DIR = Path(apps.get_app_config("bible").path) / "data"
DEFAULT_JSON = DATA_DIR / "bible.json"


class Command(BaseCommand):
    help = "Seed the Whoosh search index with bible verses from bible.json."

    def add_arguments(self, parser):
        parser.add_argument(
            "json_file",
            nargs="?",
            default=str(DEFAULT_JSON),
            help="Path to the bible JSON file (default: apps/bible/data/bible.json)",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=1000,
            help="How many verses to push per backend update call",
        )
        parser.add_argument(
            "--using",
            default="default",
            help="Haystack connection alias to write to",
        )

    def handle(self, *args, **options):
        json_file = options["json_file"]
        batch_size = options["batch_size"]
        using = options["using"]

        try:
            with open(json_file, "r", encoding="utf-8") as fh:
                entries = json.load(fh)
        except FileNotFoundError as exc:
            raise CommandError(f"JSON file not found: {json_file}") from exc
        except json.JSONDecodeError as exc:
            raise CommandError(f"Invalid JSON in {json_file}: {exc}") from exc

        backend = connections[using].get_backend()
        backend.clear(models=[Verse], commit=True)

        index = VerseIndex()
        batch = []
        total = 0
        for entry in entries:
            pk_id = entry.get("id")
            text = entry.get("_text_", "")
            if not pk_id:
                continue

            parts = pk_id.split(":")
            if len(parts) != 4:
                self.stderr.write(self.style.WARNING(f"skipping malformed id: {pk_id}"))
                continue

            version, book, chapter_s, verse_s = parts
            try:
                chapter = int(chapter_s)
                verse_num = int(verse_s)
            except ValueError:
                self.stderr.write(
                    self.style.WARNING(f"skipping non-int chapter/verse in: {pk_id}")
                )
                continue

            batch.append(
                Verse(
                    pk_id=pk_id,
                    version=version,
                    book=book,
                    chapter=chapter,
                    verse=verse_num,
                    text=text,
                )
            )

            if len(batch) >= batch_size:
                backend.update(index, batch, commit=False)
                total += len(batch)
                self.stdout.write(f"indexed {total} verses...")
                batch = []

        if batch:
            backend.update(index, batch, commit=False)
            total += len(batch)

        # Final commit so Whoosh flushes the segment.
        backend.update(index, [], commit=True)
        self.stdout.write(
            self.style.SUCCESS(f"Haystack index seeded. {total} verses written.")
        )
