"""Various operations related to looking up bible verses"""

import logging
import re

from django_redis import get_redis_connection

from . import levenshtein

logger = logging.getLogger(__name__)


def lookup(query, version="nasb95"):
    """Search a string for an apparentl bible verse location in scripture."""

    # check if the query is a specific bible resource
    verse_matches = re.findall(
        r"(\d*)[ ]*([a-zA-Z\s]+)[ ]*(-?\d+)\:?(-?\d*)", query.strip()
    )
    results = []
    if verse_matches and (len(verse_matches[0]) == 4):
        verse_matches = verse_matches[0]

        # normalize the string to avoid spelling/spacing/case inconsistencies
        book = (verse_matches[0] + verse_matches[1]).strip().lower()

        # find the mapping that fits best
        redis_conn = get_redis_connection("default")
        if not redis_conn.exists(f"{version}:{book}:1"):
            book = (verse_matches[0] + " " + verse_matches[1]).strip().lower()
            short_code = redis_conn.hget(f"{version}:books:{book}", "code")
            if short_code:
                book = short_code
            else:
                best_key = None
                book_names = [
                    key[len(f"{version}:books:") :]
                    for key in redis_conn.scan_iter(match=f"{version}:books:*")
                ]

                # is anything a prefix to the display name
                if len(book) >= 3:
                    for book_name in book_names:
                        if book_name.startswith(book):
                            best_key = book_name
                            break

                if not best_key:
                    best_distance = 100
                    # levenshtein the closest book name
                    for book_name in book_names:
                        dist = levenshtein.distance(book_name, book)
                        if dist < best_distance:
                            best_distance = dist
                            best_key = book_name

                if best_key:
                    book = redis_conn.hget(f"{version}:books:{best_key}", "code")

        chapter = verse_matches[2] if verse_matches[2] else "1"

        if verse_matches[3]:
            results.append((version, book, chapter, verse_matches[3]))
        else:
            for idx, _ in enumerate(
                redis_conn.scan_iter(match=f"{version}:{book}:{chapter}:*")
            ):
                results.append((version, book, chapter, idx + 1))

    return results
