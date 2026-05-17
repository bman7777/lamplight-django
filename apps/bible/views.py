"""Implementations of various Bible handlers."""

import logging

from django.http import HttpResponse, JsonResponse
from django_redis import get_redis_connection

from .utilities import bible_locator, haystack_search

logger = logging.getLogger(__name__)


def search(request):
    """Search for bible verses given a wide variety of
    input strings that are interpretted on-the-fly."""

    query = request.GET.get("q")
    results = []
    if query:
        results = bible_locator.lookup(query)
        if not results:
            results = haystack_search.fulltext_lookup(query)

    if not results:
        return HttpResponse(status=204)

    data = []
    redis_conn = get_redis_connection("default")
    for result in results:
        text = redis_conn.hget(
            f"{result[0]}:{result[1]}:{result[2]}:{result[3]}", "data"
        )
        # logger.info(f"{result[0]}:{result[1]}:{result[2]}:{result[3]}")
        if (
            text is None
        ):  # note: none means key doesn't exist, "" is valid for verses like Rev 12:18
            return HttpResponse(status=404)

        book_name = redis_conn.hget(f"{result[0]}:{result[1]}", "data")
        if book_name:
            data.append(
                {
                    "book": " ".join(
                        word.capitalize() for word in book_name.split(" ")
                    ),
                    "chapter": int(result[2]),
                    "verse": int(result[3]),
                    "text": text,
                }
            )

    return JsonResponse({"data": data}, status=201)
