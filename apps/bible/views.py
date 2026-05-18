"""Implementations of various Bible handlers."""

import logging
import random

from django.http import HttpResponse, JsonResponse
from django_redis import get_redis_connection

from lamplight.decorators import validate_params

from .schemas import VersesQuery
from .utilities import bible_locator, datasets, haystack_search

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


@validate_params(VersesQuery, path_fields=("book", "chapter", "verse"))
def verses(request, params):  # pylint: disable=unused-argument
    """Return a paginated list of verses matching the path + dataset filter.

    Path segments accept '*' as a wildcard. Query params: dataset
    (bible|faves|OT|NT, default bible), order (canonical|random, default
    canonical), version (default nasb95), limit (default 25, max 100),
    page (1-indexed, default 1).
    """

    pool = list(
        datasets.enumerate_verses(
            params.dataset, params.book, params.chapter, params.verse
        )
    )
    if not pool:
        return JsonResponse({"data": [], "nextPage": False})

    seed = None
    if params.order == "random":
        seed = params.seed if params.seed is not None else random.randrange(2**31)
        random.Random(seed).shuffle(pool)

    start = (params.page - 1) * params.limit
    selected = pool[start : start + params.limit]
    next_page = start + params.limit < len(pool)

    body = {
        "data": _hydrate_verses(selected, params.version),
        "nextPage": next_page,
    }
    if seed is not None:
        body["seed"] = seed
    return JsonResponse(body)


def _hydrate_verses(refs, version):
    """Look up verse text from Redis and shape the verse resource list."""

    redis_conn = get_redis_connection("default")
    data = []
    for code, ch, v in refs:
        text = redis_conn.hget(f"{version}:{code}:{ch}:{v}", "data")
        if text is None:
            logger.warning("redis missing verse %s:%s:%s:%s", version, code, ch, v)
            continue
        data.append(
            {
                "book": datasets.display_name(code),
                "chapter": ch,
                "verse": v,
                "text": text,
            }
        )
    return data
