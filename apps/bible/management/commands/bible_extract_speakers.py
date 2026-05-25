"""Extract per-verse speakers from bible.json into speaker.json."""

import json
from pathlib import Path

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError

from apps.bible.utilities.speaker_extractor import SpeakerExtractor

DATA_DIR = Path(apps.get_app_config("bible").path) / "data"
DEFAULT_INPUT = DATA_DIR / "bible.json"
DEFAULT_OUTPUT = DATA_DIR / "speaker.json"


def _parse_chapter_spec(spec):
    """Parse a --chapters arg like 'gen:1-3,exo:20,jhn:3' into a set of (book, chapter)."""
    if not spec:
        return None
    selected = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if ":" not in part:
            raise CommandError(
                f"Invalid --chapters segment {part!r}; expected BOOK:CHAPTER[-CHAPTER]"
            )
        book, ch_part = part.split(":", 1)
        book = book.strip().lower()
        ch_part = ch_part.strip()
        if "-" in ch_part:
            lo, hi = ch_part.split("-", 1)
            try:
                lo, hi = int(lo), int(hi)
            except ValueError as exc:
                raise CommandError(f"Invalid chapter range in {part!r}") from exc
            for ch in range(lo, hi + 1):
                selected.add((book, ch))
        else:
            try:
                ch = int(ch_part)
            except ValueError as exc:
                raise CommandError(f"Invalid chapter in {part!r}") from exc
            selected.add((book, ch))
    return selected


class Command(BaseCommand):
    """Management command that runs SpeakerExtractor over bible.json."""

    help = "Extract per-verse speakers from bible.json into speaker.json."

    def add_arguments(self, parser):
        parser.add_argument(
            "--input",
            default=str(DEFAULT_INPUT),
            help="Path to the bible.json file.",
        )
        parser.add_argument(
            "--output",
            default=str(DEFAULT_OUTPUT),
            help="Path to write speaker.json.",
        )
        parser.add_argument(
            "--chapters",
            default=None,
            help="Comma list like 'gen:1-3,exo:20,jhn:3'. Default: all verses.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print results and speaker counts; do not write.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Stop after N scoped verses (for smoke tests).",
        )
        parser.add_argument(
            "--print-all",
            action="store_true",
            help="Print every scoped verse (default: cap at 50 lines).",
        )

    def handle(self, *args, **options):
        in_path = Path(options["input"])
        out_path = Path(options["output"])
        scope = _parse_chapter_spec(options["chapters"])

        overrides = self._load_overrides()
        verses = self._load_verses(in_path)

        scoped_results, speaker_counts, overrides_applied = self._extract_scoped(
            verses, scope, overrides, options["limit"]
        )

        self._print_summary(
            scoped_results, speaker_counts, overrides_applied, options["print_all"]
        )

        if options["dry_run"]:
            self.stdout.write(self.style.WARNING("Dry run; not writing output."))
            return

        merged = self._merge_with_existing(out_path, scoped_results, verses)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(merged, f, indent=2, ensure_ascii=False)
            f.write("\n")
        self.stdout.write(
            self.style.SUCCESS(f"Wrote {len(merged)} entries to {out_path}.")
        )

    @staticmethod
    def _load_overrides():
        # Local import: this module is imported at Django startup, and we
        # don't want it to fail if migrations haven't run yet.
        from apps.bible.models import SpeakerOverride  # pylint: disable=import-outside-toplevel

        qs = (
            SpeakerOverride.objects.prefetch_related("speakers")
            .filter(speakers__isnull=False)
            .distinct()
        )
        return {
            ov.verse_id: sorted(s.name for s in ov.speakers.all()) for ov in qs
        }

    @staticmethod
    def _load_verses(in_path):
        try:
            with open(in_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError as exc:
            raise CommandError(f"Bible file not found: {in_path}") from exc
        except json.JSONDecodeError as exc:
            raise CommandError(f"Invalid JSON in {in_path}: {exc}") from exc

    @staticmethod
    def _extract_scoped(verses, scope, overrides, limit):
        # Pass overrides into the extractor so applied overrides re-seed
        # internal state — continuation verses after an override-corrected
        # verse inherit the corrected speaker.
        extractor = SpeakerExtractor(overrides=overrides)
        scoped_results = []
        speaker_counts = {}
        overrides_applied = 0
        for vid, speakers in extractor.extract(verses):
            _, book, chapter, _ = vid.split(":")
            if scope is not None and (book, int(chapter)) not in scope:
                continue
            if vid in overrides:
                overrides_applied += 1
            scoped_results.append({"id": vid, "speaker": speakers})
            if not speakers:
                speaker_counts["<none>"] = speaker_counts.get("<none>", 0) + 1
            else:
                for sp in speakers:
                    speaker_counts[sp] = speaker_counts.get(sp, 0) + 1
            if limit is not None and len(scoped_results) >= limit:
                break
        return scoped_results, speaker_counts, overrides_applied

    def _print_summary(
        self, scoped_results, speaker_counts, overrides_applied, print_all
    ):
        plural = "s" if overrides_applied != 1 else ""
        self.stdout.write(
            self.style.SUCCESS(
                f"Processed {len(scoped_results)} scoped verses "
                f"({overrides_applied} manual override{plural} applied)."
            )
        )
        cap = len(scoped_results) if print_all else 50
        for r in scoped_results[:cap]:
            self.stdout.write(f"  {r['id']}: {r['speaker']!r}")
        if len(scoped_results) > cap:
            self.stdout.write(f"  ... ({len(scoped_results) - cap} more)")
        self.stdout.write("")
        self.stdout.write("Top speakers:")
        for sp, count in sorted(speaker_counts.items(), key=lambda x: -x[1])[:15]:
            self.stdout.write(f"  {sp!r:30s} {count}")

    @staticmethod
    def _merge_with_existing(out_path, scoped_results, verses):
        existing_by_id = {}
        if out_path.exists():
            try:
                with open(out_path, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            except json.JSONDecodeError as exc:
                raise CommandError(f"Invalid JSON in {out_path}: {exc}") from exc
            existing_by_id = {r["id"]: r["speaker"] for r in existing}
        for r in scoped_results:
            existing_by_id[r["id"]] = r["speaker"]

        bible_order = [v["id"] for v in verses]
        bible_id_set = set(bible_order)
        merged = [
            {"id": vid, "speaker": existing_by_id[vid]}
            for vid in bible_order
            if vid in existing_by_id
        ]
        for vid in existing_by_id:
            if vid not in bible_id_set:
                merged.append({"id": vid, "speaker": existing_by_id[vid]})
        return merged
