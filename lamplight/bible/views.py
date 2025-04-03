"""Implementations of various Bible handlers."""

import logging
import os
import re

import pysolr
from django.http import JsonResponse
from django_redis import get_redis_connection

logger = logging.getLogger(__name__)


def search(request):
    """Search for bible verses given a wide variety of
    input strings that are interpretted on-the-fly."""

    query = request.GET.get("q")
    if query:
        # check if the query is a specific bible resource
        verse_matches = re.findall(
            r"(\d*)[ ]*([\w\s]+)[ ]*(\d+)\:?(\d*)", query.strip()
        )
        if verse_matches and (len(verse_matches[0]) == 4):
            verse_matches = verse_matches[0]

            # normalize the string to avoid spelling/spacing inconsistencies
            book = (verse_matches[0] + " " + verse_matches[1]).strip()
            book = " ".join(word.capitalize() for word in book.split(" "))

            chapter = verse_matches[2] if verse_matches[2] else "1"

            # todo: return a list of verses if asking for the whole chapter
            verse = verse_matches[3] if verse_matches[3] else "1"

            if book == "Luke" and chapter == "1":
                text = get_redis_connection("default").hget(
                    f"nasb95:luk:{chapter}:{verse}", "data"
                )
            else:
                text = "todo"

            return JsonResponse(
                {
                    "data": [
                        {
                            "book": book,
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
            "fl": "id,_text_",  # Fields to return
            "sort": "score desc",  # Optional sorting
        },
    )
    out = []
    for result in results:
        parts = result["id"].split(":")
        out.append(
            {
                "book": "Luke",
                "chapter": int(parts[2]),
                "verse": int(parts[3]),
                "text": get_redis_connection("default").hget(result["id"], "data"),
            }
        )
        logger.info(result)

    return JsonResponse({"data": out}, status=201)
