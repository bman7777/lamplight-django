"""Build the concord_id <-> verse mapping by parsing bible.csv."""

import csv
from pathlib import Path

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.bible.models import ConcordanceEntry, ConcordanceVerseMapping, Verse
from apps.bible.utilities.concord import CONCORD_TAG_RE, normalize_concord_id

DATA_DIR = Path(apps.get_app_config("bible").path) / "data"
DEFAULT_CSV_PATH = DATA_DIR / "bible.csv"

BATCH_SIZE = 1000


class Command(BaseCommand):
    """Management command that maps Strong's concord IDs to the verses they appear in."""

    help = "Build the (concord_id, verse) mapping table from bible.csv markup."

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv-file",
            default=str(DEFAULT_CSV_PATH),
            help="Path to the bible CSV file.",
        )
        parser.add_argument(
            "--prefix",
            default="nasb95",
            help="Version prefix stored on each mapping row (matches bible_to_redis).",
        )

    def handle(self, *args, **options):
        csv_file = options["csv_file"]
        version = options["prefix"]
        known_concord_ids = set(
            ConcordanceEntry.objects.values_list("concord_id", flat=True)
        )
        known_verse_ids = set(
            Verse.objects.filter(version=version).values_list("pk_id", flat=True)
        )

        mappings, row_count, skipped_invalid, skipped_unknown, skipped_no_verse = (
            self._parse_csv(csv_file, version, known_concord_ids, known_verse_ids)
        )

        with transaction.atomic():
            ConcordanceVerseMapping.objects.filter(verse__version=version).delete()
            ConcordanceVerseMapping.objects.bulk_create(mappings, batch_size=BATCH_SIZE)

        self.stdout.write(
            self.style.SUCCESS(
                f"Verse mapping complete for version '{version}'. "
                f"Inserted {len(mappings)} rows across {row_count} verses. "
                f"Skipped {skipped_invalid} invalid tags, "
                f"{skipped_unknown} unknown concord IDs, "
                f"{skipped_no_verse} rows with no matching Verse."
            )
        )

    def _parse_csv(self, csv_file, version, known_concord_ids, known_verse_ids):
        # pylint: disable=duplicate-code
        try:
            file = open(csv_file, "r", newline="", encoding="utf-8")
        except FileNotFoundError as exc:
            raise CommandError(f"CSV file not found: {csv_file}") from exc

        # Preserve escaped characters (otherwise we will lose all commas).
        csv.register_dialect(
            "escaped", escapechar="\\", doublequote=False, quoting=csv.QUOTE_MINIMAL
        )

        mappings = []
        row_count = 0
        skipped_invalid = 0
        skipped_unknown = 0
        skipped_no_verse = 0

        with file:
            reader = csv.reader(file, dialect="escaped")
            for row in reader:
                if not row or len(row) < 4:
                    continue
                row_invalid, row_unknown, row_no_verse = self._collect_row_mappings(
                    row, version, known_concord_ids, known_verse_ids, mappings
                )
                skipped_invalid += row_invalid
                skipped_unknown += row_unknown
                skipped_no_verse += row_no_verse
                row_count += 1
                if row_count % 1000 == 0:
                    self.stdout.write(f"Processed {row_count} verses...")

        return mappings, row_count, skipped_invalid, skipped_unknown, skipped_no_verse

    @staticmethod
    def _collect_row_mappings(
        row, version, known_concord_ids, known_verse_ids, mappings
    ):
        book, text = row[0], row[3]
        try:
            chapter_i, verse_i = int(row[1]), int(row[2])
        except ValueError:
            return 1, 0, 0

        verse_id = f"{version}:{book}:{chapter_i}:{verse_i}"
        if verse_id not in known_verse_ids:
            # If the verse isn't in the DB, skip every concord tag on this row
            # (count once per tag for symmetry with the other skip counters).
            return 0, 0, sum(1 for _ in CONCORD_TAG_RE.findall(text))

        skipped_invalid = 0
        skipped_unknown = 0
        seen_in_verse = set()
        for raw_id in CONCORD_TAG_RE.findall(text):
            norm = normalize_concord_id(raw_id)
            if not norm:
                skipped_invalid += 1
                continue
            if norm in seen_in_verse:
                continue
            if norm not in known_concord_ids:
                skipped_unknown += 1
                continue
            seen_in_verse.add(norm)
            mappings.append(
                ConcordanceVerseMapping(concord_id=norm, verse_id=verse_id)
            )
        return skipped_invalid, skipped_unknown, 0
