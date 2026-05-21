"""Apply a list of SearchCriterion to the bible corpus.

Each criterion either *produces* a candidate verse set (``text``, ``english``,
``hebrew``, ``greek``, ``author``) or *restricts* an existing set (``book``,
``testament``). Multiple criteria are AND'd together. Criteria for which we
don't yet have data (``speaker``) are silently dropped — the TODO comment
below marks where the missing data source needs to plug in.
"""

from functools import lru_cache

from ..models import Author, Authorship, ConcordanceVerseMapping
from . import bible_locator, datasets, haystack_search
from .concord import normalize_concord_id

VERSION = "nasb95"
INTERNAL_CAP = 10000  # max producer hits considered before pagination


def combine(criteria, page, limit):
    """Resolve criteria into (total, page_refs).

    Refs are ``(version, book_code, chapter, verse)`` tuples in canonical order.
    """

    producers = [c for c in criteria if c.type in _PRODUCERS]
    restrictors = [c for c in criteria if c.type in {"book", "testament"}]

    if producers:
        candidate = None
        for p in producers:
            hits = _producer_hits(p)
            candidate = hits if candidate is None else candidate & hits
            if not candidate:
                return 0, []
        for r in restrictors:
            pred = _restrictor_predicate(r)
            candidate = {ref for ref in candidate if pred(ref)}
    elif restrictors:
        candidate = _enumerate_restrictor_pool(restrictors)
    else:
        return 0, []

    sorted_refs = sorted(candidate, key=_canonical_key)
    total = len(sorted_refs)
    start = (page - 1) * limit
    return total, sorted_refs[start : start + limit]


def _producer_hits(criterion):
    handler = _PRODUCERS.get(criterion.type)
    return handler(criterion) if handler else set()


def _text_hits(criterion):
    refs = bible_locator.lookup(criterion.value)
    if not refs:
        refs = haystack_search.fulltext_lookup(criterion.value, limit=INTERNAL_CAP)
    return {_normalize(*r) for r in refs}


def _english_hits(criterion):
    refs = haystack_search.fulltext_lookup(criterion.value, limit=INTERNAL_CAP)
    return {_normalize(*r) for r in refs}


def _concord_hits(criterion):
    concord_id = normalize_concord_id(criterion.concordance_id)
    if not concord_id:
        return set()
    rows = ConcordanceVerseMapping.objects.filter(
        concord_id=concord_id, version=VERSION
    ).values_list("book", "chapter", "verse")
    return {_normalize(VERSION, book, ch, v) for book, ch, v in rows}


def _author_hits(criterion):
    author_id = (
        Author.objects.filter(name__iexact=criterion.value.strip())
        .values_list("id", flat=True)
        .first()
    )
    if author_id is None:
        return set()
    result = set()
    for row in Authorship.objects.only("book_name", "chapter", "author"):
        if author_id not in row.author:
            continue
        chapter = "*" if row.chapter is None else row.chapter
        for code, ch, v in datasets.enumerate_verses(
            "bible", row.book_name, chapter, "*"
        ):
            result.add(_normalize(VERSION, code, ch, v))
    return result


_PRODUCERS = {
    "text": _text_hits,
    "english": _english_hits,
    "hebrew": _concord_hits,
    "greek": _concord_hits,
    "author": _author_hits,
}


def _restrictor_predicate(criterion):
    if criterion.type == "book":
        target = criterion.value
        return lambda ref: ref[1] == target
    if criterion.type == "testament":
        dataset = "OT" if criterion.value == "old" else "NT"
        codes = set(datasets.books_in_dataset(dataset))
        return lambda ref: ref[1] in codes
    return lambda ref: True


def _enumerate_restrictor_pool(restrictors):
    book_code = "*"
    dataset = "bible"
    for c in restrictors:
        if c.type == "book":
            book_code = c.value
        elif c.type == "testament":
            dataset = "OT" if c.value == "old" else "NT"
    return {
        (VERSION, code, ch, v)
        for code, ch, v in datasets.enumerate_verses(dataset, book_code, "*", "*")
    }


def _normalize(version, book, chapter, verse):
    return (version, book, int(chapter), int(verse))


@lru_cache(maxsize=1)
def _canon_order():
    return {code: i for i, code in enumerate(datasets.books_in_dataset("bible"))}


def _canonical_key(ref):
    return (_canon_order().get(ref[1], 999), ref[2], ref[3])


# TODO: speaker criterion needs per-pericope speaker annotation; no data source yet.
