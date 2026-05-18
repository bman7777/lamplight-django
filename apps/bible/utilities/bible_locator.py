"""Various operations related to looking up bible verses"""

import logging
import re

from django_redis import get_redis_connection

from . import levenshtein

logger = logging.getLogger(__name__)


def lookup(query, version="nasb95"):
    """Search a string for an apparent bible verse location in scripture."""

    matches = re.findall(r"(\d*)[ ]*([a-zA-Z\s]+)[ ]*(-?\d+)\:?(-?\d*)", query.strip())
    if not matches or len(matches[0]) != 4:
        return []

    prefix_digits, name, chapter_str, verse_str = matches[0]
    redis_conn = get_redis_connection("default")
    book = _resolve_book(redis_conn, version, prefix_digits, name)
    chapter = chapter_str if chapter_str else "1"

    if verse_str:
        return [(version, book, chapter, verse_str)]

    return [
        (version, book, chapter, idx + 1)
        for idx, _ in enumerate(
            redis_conn.scan_iter(match=f"{version}:{book}:{chapter}:*")
        )
    ]


def _resolve_book(redis_conn, version, prefix_digits, name):
    """Map a raw "1 john" / "luek" / "jhn" style fragment to a redis short code."""

    candidate = (prefix_digits + name).strip().lower()
    if redis_conn.exists(f"{version}:{candidate}:1"):
        return candidate

    spaced = (prefix_digits + " " + name).strip().lower()
    short_code = redis_conn.hget(f"{version}:books:{spaced}", "code")
    if short_code:
        return short_code

    book_names = [
        key[len(f"{version}:books:") :]
        for key in redis_conn.scan_iter(match=f"{version}:books:*")
    ]
    best_key = _best_match(spaced, book_names)
    if best_key:
        return redis_conn.hget(f"{version}:books:{best_key}", "code")
    return spaced


def _best_match(book, book_names):
    """Return the best display-name match for `book`, preferring prefix over levenshtein."""

    if len(book) >= 3:
        for name in book_names:
            if name.startswith(book):
                return name

    best_key = None
    best_distance = 100
    for name in book_names:
        dist = levenshtein.distance(name, book)
        if dist < best_distance:
            best_distance = dist
            best_key = name
    return best_key
