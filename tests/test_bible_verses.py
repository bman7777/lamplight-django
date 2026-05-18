"""End-to-end tests for the /ll/bible/<book>/<chapter>/<verse>/ endpoint.

Assumes Redis is seeded by `bible_to_redis` (same precondition as
test_bible_search.py) so verse text lookups succeed.
"""

from urllib.parse import urlencode

import pytest
from django.urls import reverse


def _url(book, chapter, verse, **params):
    """Build a `verses` URL with optional query params."""

    base = reverse("verses", kwargs={"book": book, "chapter": chapter, "verse": verse})
    return f"{base}?{urlencode(params)}" if params else base


@pytest.mark.parametrize(
    "book,chapter,verse,expected_book",
    [
        ("john", "3", "16", "John"),
        ("jhn", "3", "16", "John"),  # short code
        ("1 John", "4", "8", "1 John"),  # display name with leading number
        ("1john", "4", "8", "1 John"),  # no-space variant
    ],
)
def test_specific_verse_resolves_book(client, book, chapter, verse, expected_book):
    """Fully-specified paths return the right verse across book-name variants."""

    response = client.get(_url(book, chapter, verse))
    assert response.status_code == 200
    body = response.json()
    assert body["nextPage"] is False
    assert len(body["data"]) == 1
    item = body["data"][0]
    assert item["book"] == expected_book
    assert item["chapter"] == int(chapter)
    assert item["verse"] == int(verse)
    assert item["text"]


@pytest.mark.parametrize(
    "path,expected_count,expected_book",
    [
        (("john", "3", "*"), 36, "John"),  # full chapter (John 3 has 36 verses)
        (("jude", "*", "*"), 25, "Jude"),  # full book (Jude is 1 chapter, 25 verses)
    ],
)
def test_wildcards_expand_pool(client, path, expected_count, expected_book):
    """`*` segments expand the pool to every matching verse."""

    body = client.get(_url(*path, limit=100)).json()
    assert len(body["data"]) == expected_count
    assert body["nextPage"] is False
    assert all(item["book"] == expected_book for item in body["data"])


@pytest.mark.parametrize(
    "page,expected_verses,expected_next",
    [
        (1, list(range(1, 11)), True),
        (2, list(range(11, 21)), True),
        (4, list(range(31, 37)), False),  # John 3 has 36 verses
    ],
)
def test_pagination(client, page, expected_verses, expected_next):
    """limit/page paginate the pool and nextPage flips on the last slice."""

    body = client.get(_url("john", "3", "*", limit=10, page=page)).json()
    assert [v["verse"] for v in body["data"]] == expected_verses
    assert body["nextPage"] is expected_next


@pytest.mark.parametrize(
    "dataset,expected_book",
    [("OT", "Genesis"), ("NT", "Matthew")],
)
def test_dataset_starts_at_first_book(client, dataset, expected_book):
    """OT/NT iterate their books in canonical order from the first book."""

    body = client.get(_url("*", "*", "*", dataset=dataset, limit=3)).json()
    assert body["nextPage"] is True
    assert body["data"][0]["book"] == expected_book
    assert body["data"][0]["chapter"] == 1
    assert body["data"][0]["verse"] == 1


def test_explicit_version_param(client):
    """Passing the only supported version explicitly returns the same payload."""

    body = client.get(_url("john", "3", "16", version="nasb95")).json()
    assert body["data"][0]["book"] == "John"
    assert body["data"][0]["chapter"] == 3
    assert body["data"][0]["verse"] == 16


def test_dataset_faves(client):
    """dataset=faves returns the curated list and respects book filters."""

    all_faves = client.get(_url("*", "*", "*", dataset="faves", limit=100)).json()
    refs = {(v["book"], v["chapter"], v["verse"]) for v in all_faves["data"]}
    assert {("John", 3, 16), ("Genesis", 1, 1)}.issubset(refs)
    assert all_faves["nextPage"] is False

    only_john = client.get(_url("john", "*", "*", dataset="faves", limit=100)).json()
    assert {v["book"] for v in only_john["data"]} == {"John"}

    # Zechariah isn't in the faves list, so the filtered pool is empty.
    empty = client.get(_url("zechariah", "*", "*", dataset="faves")).json()
    assert empty == {"data": [], "nextPage": False}


def test_order_random_returns_same_pool_in_different_order(client):
    """order=random returns the same verses as canonical but shuffled."""

    # John 3's 36 verses make accidental in-order shuffle vanishingly unlikely.
    canonical = client.get(_url("john", "3", "*", limit=36)).json()
    random_resp = client.get(_url("john", "3", "*", limit=36, order="random")).json()

    canonical_refs = {(v["chapter"], v["verse"]) for v in canonical["data"]}
    random_refs = {(v["chapter"], v["verse"]) for v in random_resp["data"]}
    assert canonical_refs == random_refs
    assert [v["verse"] for v in random_resp["data"]] != list(range(1, 37))
    assert "seed" in random_resp
    assert "seed" not in canonical


def test_order_random_seed_enables_stable_pagination(client):
    """Reusing the returned seed makes random pagination cover the pool without overlap."""

    page1 = client.get(_url("john", "3", "*", limit=20, order="random")).json()
    seed = page1["seed"]
    assert page1["nextPage"] is True

    page2 = client.get(
        _url("john", "3", "*", limit=20, order="random", page=2, seed=seed)
    ).json()
    assert page2["seed"] == seed
    assert page2["nextPage"] is False

    combined = [(v["chapter"], v["verse"]) for v in page1["data"] + page2["data"]]
    # John 3 has 36 verses; the two pages should partition the pool exactly once.
    assert len(combined) == 36
    assert set(combined) == {(3, v) for v in range(1, 37)}


def test_order_random_same_seed_reproduces_order(client):
    """Two random calls with the same seed return the same verse order."""

    a = client.get(_url("john", "3", "*", limit=36, order="random", seed=42)).json()
    b = client.get(_url("john", "3", "*", limit=36, order="random", seed=42)).json()
    assert a["data"] == b["data"]
    assert a["seed"] == b["seed"] == 42


@pytest.mark.parametrize(
    "path,params",
    [
        (("notabook", "1", "1"), {}),
        (("john", "abc", "1"), {}),
        (("john", "3", "16"), {"dataset": "bogus"}),
        (("john", "3", "16"), {"order": "sideways"}),
        (("john", "3", "16"), {"limit": "0"}),
        (("john", "3", "16"), {"limit": "-1"}),
        (("john", "3", "16"), {"limit": "101"}),
        (("john", "3", "16"), {"limit": "abc"}),
        (("john", "3", "16"), {"page": "0"}),
        (("john", "3", "16"), {"page": "-1"}),
        (("john", "3", "16"), {"page": "abc"}),
        (("john", "3", "16"), {"version": "kjv"}),
        (("john", "3", "16"), {"seed": "-1"}),
        (("john", "3", "16"), {"seed": "abc"}),
    ],
)
def test_invalid_input_returns_400(client, path, params):
    """All input validation failures produce a 400."""

    response = client.get(_url(*path, **params))
    assert response.status_code == 400
