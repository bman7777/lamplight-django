"""Fulltext search over the haystack (Whoosh) index for bible verses."""

import logging

from haystack.query import SearchQuerySet

logger = logging.getLogger(__name__)

DEFAULT_LIMIT = 25


def _hits_to_tuples(sqs):
    return [
        (hit.version, hit.book, int(hit.chapter), int(hit.verse))
        for hit in sqs
        if hit is not None
    ]


def fulltext_lookup(query, limit=DEFAULT_LIMIT):
    """Run a fulltext search and return (version, book, chapter, verse) tuples.

    Phrase matches (the input treated as a contiguous phrase) are preferred and
    returned first; if none are found, falls back to individual-term matching so
    short / single-word queries still resolve. Matches the return shape of
    bible_locator.lookup so views.search can reuse its Redis-resolution code.
    """

    if not query:
        return []

    try:
        phrase_hits = SearchQuerySet().filter(content__exact=query)[:limit]
        results = _hits_to_tuples(phrase_hits)
        if results:
            return results

        term_hits = SearchQuerySet().filter(content=query)[:limit]
        return _hits_to_tuples(term_hits)
    except Exception:
        logger.exception("haystack fulltext lookup failed for query=%r", query)
        return []
