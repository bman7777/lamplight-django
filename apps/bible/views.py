"""Implementations of various Bible handlers."""

import json
import logging
import random

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django_redis import get_redis_connection
from pydantic import ValidationError

from lamplight.decorators import validate_params

from .models import ConcordanceEntry
from .schemas import (ConcordanceEntryResponse, SearchPageQuery, SearchRequest,
                      VersesQuery)
from .utilities import datasets, search_criteria

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["POST"])
def search(request):
    """Filter bible verses by an AND'd list of search criteria.

    Request body: ``{"criteria": [SearchCriterion, ...]}``. Query params
    ``page`` (>=1, default 1) and ``limit`` (1..100, default 25) control
    pagination. Response: ``{"total": int, "verses": [...]}``.
    """

    try:
        body = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "body must be valid JSON"}, status=400)

    try:
        payload = SearchRequest.model_validate(body)
        page_query = SearchPageQuery.model_validate(request.GET.dict())
    except ValidationError as exc:
        first = exc.errors()[0]
        field = first["loc"][0] if first["loc"] else "input"
        return JsonResponse({"error": f"{field}: {first['msg']}"}, status=400)

    total, refs = search_criteria.combine(
        payload.criteria, page_query.page, page_query.limit
    )
    verses_out = _hydrate_verses(
        [(code, ch, v) for _, code, ch, v in refs], search_criteria.VERSION
    )
    return JsonResponse({"total": total, "verses": verses_out})


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


def concordance(request, concord_id):  # pylint: disable=unused-argument
    """Return the Strong's concordance entry for the given ID (e.g. G0001, H0001)."""

    prefix, digits = concord_id[:1].upper(), concord_id[1:]
    if prefix in ("G", "H") and digits.isdigit():
        concord_id = f"{prefix}{int(digits):04d}"
    entry = get_object_or_404(ConcordanceEntry, pk=concord_id)
    return JsonResponse(ConcordanceEntryResponse.model_validate(entry).model_dump())


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
