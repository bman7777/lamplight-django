"""Named verse datasets and book/path resolution for the verses endpoint.

The bible structure (book -> chapter -> max verse) is built lazily from
apps/bible/data/bible.json on first use and memoized per worker process.
"""

import json
from functools import lru_cache
from pathlib import Path

from django.apps import apps

DATA_DIR = Path(apps.get_app_config("bible").path) / "data"
BOOK_MAP_PATH = DATA_DIR / "book_map.json"
BIBLE_JSON_PATH = DATA_DIR / "bible.json"

# Protestant canon: the first 39 entries of book_map.json are the OT.
_OT_BOOK_COUNT = 39

# Curated favorites — well-known verses surfaced by dataset=faves.
FAVES = (
    ("gen", 1, 1),
    ("psa", 23, 1),
    ("psa", 46, 10),
    ("psa", 119, 105),
    ("pro", 3, 5),
    ("pro", 3, 6),
    ("isa", 40, 31),
    ("isa", 41, 10),
    ("jer", 29, 11),
    ("mat", 6, 33),
    ("mat", 28, 19),
    ("jhn", 1, 1),
    ("jhn", 3, 16),
    ("jhn", 14, 6),
    ("act", 1, 8),
    ("rom", 3, 23),
    ("rom", 5, 8),
    ("rom", 8, 28),
    ("rom", 10, 9),
    ("1co", 13, 4),
    ("1co", 13, 13),
    ("gal", 2, 20),
    ("eph", 2, 8),
    ("phl", 4, 13),
    ("heb", 11, 1),
    ("jas", 1, 5),
    ("1jo", 4, 8),
    ("rev", 3, 20),
)


@lru_cache(maxsize=1)
def _book_map():
    with open(BOOK_MAP_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def _codes_in_order():
    return tuple(list(entry.values())[0] for entry in _book_map())


@lru_cache(maxsize=1)
def _display_name_by_code():
    return {list(entry.values())[0]: list(entry.keys())[0] for entry in _book_map()}


@lru_cache(maxsize=1)
def _code_by_display_name():
    return {list(entry.keys())[0]: list(entry.values())[0] for entry in _book_map()}


@lru_cache(maxsize=1)
def _structure():
    """Return mapping {book_code: {chapter: max_verse}} from bible.json."""

    with open(BIBLE_JSON_PATH, "r", encoding="utf-8") as f:
        verses = json.load(f)

    structure = {}
    for entry in verses:
        _, book, chapter, verse = entry["id"].split(":")
        chapter = int(chapter)
        verse = int(verse)
        chapters = structure.setdefault(book, {})
        if verse > chapters.get(chapter, 0):
            chapters[chapter] = verse
    return structure


def _strip_non_alnum(s):
    return "".join(ch for ch in s if ch.isalnum())


def resolve_book(value):
    """Normalize a path-provided book to its short code, or None if unknown.

    Accepts the wildcard '*' (returned as-is), short codes ('gen'), and display
    names with flexible spacing/case ('Genesis', '1 John', '1john', 'song-of-songs').
    """

    if value == "*":
        return "*"

    normalized = value.strip().lower()
    if not normalized:
        return None

    if normalized in _display_name_by_code():
        return normalized

    name_to_code = _code_by_display_name()
    if normalized in name_to_code:
        return name_to_code[normalized]

    stripped = _strip_non_alnum(normalized)
    for display, code in name_to_code.items():
        if _strip_non_alnum(display) == stripped:
            return code
    return None


def display_name(book_code):
    """Return the title-cased display name for a book short code."""

    raw = _display_name_by_code().get(book_code, book_code)
    return " ".join(word.capitalize() for word in raw.split(" "))


def books_in_dataset(dataset):
    """Ordered list of book codes belonging to the dataset (empty for 'faves')."""

    codes = _codes_in_order()
    if dataset == "bible":
        return list(codes)
    if dataset == "OT":
        return list(codes[:_OT_BOOK_COUNT])
    if dataset == "NT":
        return list(codes[_OT_BOOK_COUNT:])
    return []


def _matches(ref, book, chapter, verse):
    code, ch, v = ref
    if book not in ("*", code):
        return False
    if chapter not in ("*", ch):
        return False
    if verse not in ("*", v):
        return False
    return True


def enumerate_verses(dataset, book, chapter, verse):
    """Yield (book_code, chapter, verse) triples matching the path filter.

    Path values use '*' as a wildcard. Output is in canonical order
    (book, then chapter, then verse). Pagination/shuffling is the caller's job.
    """

    if dataset == "faves":
        for ref in FAVES:
            if _matches(ref, book, chapter, verse):
                yield ref
        return

    structure = _structure()
    for code in books_in_dataset(dataset):
        if book not in ("*", code):
            continue
        chapters = structure.get(code, {})
        for ch in sorted(chapters):
            if chapter not in ("*", ch):
                continue
            for v in range(1, chapters[ch] + 1):
                if verse not in ("*", v):
                    continue
                yield (code, ch, v)
