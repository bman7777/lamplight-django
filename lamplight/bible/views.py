"""Implementations of various Bible handlers."""

import logging
import os
import re

import pysolr
from django.http import HttpResponse, JsonResponse
from django_redis import get_redis_connection

from .utilities import levenshtein

logger = logging.getLogger(__name__)


def search(request):
    """Search for bible verses given a wide variety of
    input strings that are interpretted on-the-fly."""

    redis_conn = get_redis_connection("default")
    query = request.GET.get("q")
    if query:
        # check if the query is a specific bible resource
        verse_matches = re.findall(
            r"(\d*)[ ]*([\w\s]+)[ ]*(-?\d+)\:?(-?\d*)", query.strip()
        )
        if verse_matches and (len(verse_matches[0]) == 4):
            verse_matches = verse_matches[0]

            # normalize the string to avoid spelling/spacing/case inconsistencies
            book = (verse_matches[0] + verse_matches[1]).strip().lower()

            # find the short code
            if not redis_conn.exists(f"nasb95:{book}:1"):
                book = (verse_matches[0] + " " + verse_matches[1]).strip().lower()
                short_code = redis_conn.hget(f"nasb95:books:{book}", "code")
                if short_code:
                    book = short_code
                else:
                    best_key = None
                    best_distance = 100
                    # levenshtein the closest book name
                    for key in redis_conn.scan_iter(match="nasb95:books:*"):
                        check_book = key[len("nasb95:books:") :]
                        dist = levenshtein.distance(check_book, book)
                        if dist < best_distance:
                            best_distance = dist
                            best_key = check_book

                    if best_key:
                        book = redis_conn.hget(f"nasb95:books:{best_key}", "code")

            chapter = verse_matches[2] if verse_matches[2] else "1"

            # todo: return a list of verses if asking for the whole chapter
            verse = verse_matches[3] if verse_matches[3] else "1"

            text = redis_conn.hget(f"nasb95:{book}:{chapter}:{verse}", "data")
            if not text:
                return HttpResponse(status=404)

            book_name = redis_conn.hget(f"nasb95:{book}", "data") or ""
            return JsonResponse(
                {
                    "data": [
                        {
                            "book": " ".join(
                                word.capitalize() for word in book_name.split(" ")
                            ),
                            "chapter": int(chapter),
                            "verse": int(verse),
                            "text": text,
                        }
                    ]
                },
                status=201,
            )

    solr = pysolr.Solr(
        "http://localhost:8983/solr/verses/",
        timeout=10,
        auth=(os.getenv("SOLR_USER"), os.getenv("SOLR_PASS")),
    )
    results = solr.search(
        query,
        **{
            "pf": "_text_^10",  # boost exact phrase matches higher
            "fl": "id,_text_",  # Fields to return
            "sort": "score desc",  # Optional sorting
            "defType": "edismax",  # query parser to use
            "ps": 10,  # phrase slop: only exact phrases get the boost
        },
    )
    out = []
    for result in results:
        parts = result["id"].split(":")
        book_name = redis_conn.hget(f"nasb95:{parts[1]}", "data")
        out.append(
            {
                "book": " ".join(word.capitalize() for word in book_name.split(" ")),
                "chapter": int(parts[2]),
                "verse": int(parts[3]),
                "text": redis_conn.hget(result["id"], "data"),
            }
        )

    return JsonResponse({"data": out}, status=201)
