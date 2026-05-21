"""Apply a list of SearchCriterion to the bible corpus.

Each criterion either *produces* a candidate verse set (``text``, ``english``)
or *restricts* an existing set (``book``, ``testament``). Multiple criteria
are AND'd together. Criteria for which we don't yet have data
(``hebrew``, ``greek``, ``author``, ``speaker``) are silently dropped — the
TODO comments below mark where each missing data source needs to plug in.
"""

from functools import lru_cache

from . import bible_locator, datasets, haystack_search

VERSION = "nasb95"
INTERNAL_CAP = 10000  # max producer hits considered before pagination


def combine(criteria, page, limit):
    """Resolve criteria into (total, page_refs).

    Refs are ``(version, book_code, chapter, verse)`` tuples in canonical order.
    """

    producers = [c for c in criteria if c.type in {"text", "english"}]
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
    if criterion.type == "text":
        refs = bible_locator.lookup(criterion.value)
        if refs:
            return {_normalize(*r) for r in refs}
        refs = haystack_search.fulltext_lookup(criterion.value, limit=INTERNAL_CAP)
        return {_normalize(*r) for r in refs}
    if criterion.type == "english":
        refs = haystack_search.fulltext_lookup(criterion.value, limit=INTERNAL_CAP)
        return {_normalize(*r) for r in refs}
    return set()


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


# TODO: hebrew / greek criteria need per-verse Strong's concordance tagging in
# bible.json (each verse gets a list of concord_ids) before we can filter on them.
# TODO: author criterion needs a book-author mapping (e.g. apps/bible/data/authors.json)
# that returns the human author for each book code.
# TODO: speaker criterion needs per-pericope speaker annotation; no data source yet.
