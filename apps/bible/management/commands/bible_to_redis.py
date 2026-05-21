"""Import all the verses from a csv into Redis for future quick access."""

import csv
import json
from pathlib import Path

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django_redis import get_redis_connection

DATA_DIR = Path(apps.get_app_config("bible").path) / "data"
BOOK_MAP_PATH = DATA_DIR / "book_map.json"


class Command(BaseCommand):
    """Management command that loads bible CSV verse data into Redis."""

    help = "Import bible CSV data into Redis hashes."

    def add_arguments(self, parser):
        parser.add_argument("csv_file", help="Path to the CSV file to import")
        parser.add_argument(
            "--prefix", default="nasb95", help="Prefix for Redis hash keys"
        )

    def handle(self, *args, **options):
        csv_file = options["csv_file"]
        prefix = options["prefix"]

        try:
            with open(BOOK_MAP_PATH, "r", encoding="utf-8") as f:
                book_map = json.load(f)
        except FileNotFoundError as exc:
            raise CommandError(f"book_map.json not found at {BOOK_MAP_PATH}") from exc

        redis_conn = get_redis_connection("default")
        self._import_version_info(redis_conn, book_map, prefix)
        self._import_verses(redis_conn, book_map, csv_file, prefix)

    def _import_version_info(self, redis_conn, book_map, prefix):
        redis_conn.hset(prefix, mapping={"name": prefix, "data": "NASB 95 Translation"})

        count = 0
        for book in book_map:
            name = list(book.keys())[0]
            code = list(book.values())[0]
            self.stdout.write(f"adding {prefix}:books:{name}")
            redis_conn.hset(f"{prefix}:books:{name}", mapping={"code": code})
            count += 1

        self.stdout.write(
            self.style.SUCCESS(f"Version info import complete. Processed {count} rows.")
        )

    def _import_verses(self, redis_conn, book_map, csv_file, prefix):
        # pylint: disable=duplicate-code
        try:
            file = open(csv_file, "r", newline="", encoding="utf-8")
        except FileNotFoundError as exc:
            raise CommandError(f"CSV file not found: {csv_file}") from exc

        # Preserve escaped characters (otherwise we will lose all commas)
        csv.register_dialect(
            "escaped", escapechar="\\", doublequote=False, quoting=csv.QUOTE_MINIMAL
        )

        with file:
            reader = csv.reader(file, dialect="escaped")
            row_count = 0
            for row in reader:
                if not row:
                    continue

                try:
                    text = "" if len(row) <= 3 else row[3]
                    display_name = ""

                    if row[1] == row[2] == "1":
                        for book in book_map:
                            if list(book.values())[0] == row[0]:
                                display_name = list(book.keys())[0]
                                self.stdout.write(f"adding key for: {prefix}:{row[0]}")
                                redis_conn.hset(
                                    f"{prefix}:{row[0]}",
                                    mapping={"name": row[0], "data": display_name},
                                )
                                break

                    if row[2] == "1":
                        redis_conn.hset(
                            f"{prefix}:{row[0]}:{row[1]}",
                            mapping={
                                "name": f"{row[0]} {row[1]}",
                                "data": f"{display_name} chapter {row[1]}",
                            },
                        )

                    redis_conn.hset(
                        f"{prefix}:{row[0]}:{row[1]}:{row[2]}",
                        mapping={"name": f"{row[0]} {row[1]}:{row[2]}", "data": text},
                    )
                    row_count += 1

                    if row_count % 1000 == 0:
                        self.stdout.write(f"Processed {row_count} rows...")

                except Exception as e:  # pylint: disable=broad-exception-caught
                    self.stderr.write(
                        self.style.ERROR(f"Error processing row {row_count + 1}: {e}")
                    )
                    self.stderr.write(f"Row data: {row}")

            self.stdout.write(
                self.style.SUCCESS(
                    f"Verse import complete. Processed {row_count} rows."
                )
            )
