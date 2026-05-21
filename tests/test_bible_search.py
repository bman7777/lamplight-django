"""Tests for the criterion-based search endpoint."""

import json

import pytest
from django.urls import reverse


def _post(client, criteria, query=""):
    url = reverse("search")
    if query:
        url = f"{url}?{query}"
    return client.post(
        url,
        data=json.dumps({"criteria": criteria}),
        content_type="application/json",
    )


@pytest.mark.parametrize(
    "value,book,chapter,verse",
    [
        ("Luke 1:28", "Luke", 1, 28),
        ("Matt 8:28", "Matthew", 8, 28),
        ("Rev 12:18", "Revelation", 12, 18),
        ("1 John 3:16", "1 John", 3, 16),
        ("song of songs 1:15", "Song Of Songs", 1, 15),
        ("1JOhn 3:16", "1 John", 3, 16),
    ],
)
def test_text_criterion_verse_refs(client, value, book, chapter, verse):
    """A text criterion containing a verse reference resolves to that exact verse."""
    response = _post(client, [{"type": "text", "value": value}])
    assert response.status_code == 200
    out = response.json()
    first = out["verses"][0]
    assert first["book"] == book
    assert first["chapter"] == chapter
    assert first["verse"] == verse
    assert first["text"] is not None


@pytest.mark.parametrize(
    "value,book,chapter,verse",
    [
        ("Luek 1:28", "Luke", 1, 28),
        ("ulke 1:28", "Luke", 1, 28),
        ("lk 1:28", "Luke", 1, 28),
    ],
)
def test_text_criterion_misspelled(client, value, book, chapter, verse):
    """Misspelled or abbreviated book names in a text criterion still resolve correctly."""
    response = _post(client, [{"type": "text", "value": value}])
    assert response.status_code == 200
    first = response.json()["verses"][0]
    assert first["book"] == book
    assert first["chapter"] == chapter
    assert first["verse"] == verse


@pytest.mark.parametrize(
    "value,book,chapter,verse",
    [
        ("inasmuch", "Hebrews", 7, 20),
        ("priestly", "Luke", 1, 23),
        ("for God so loved the world", "John", 3, 16),
        ("Jesus wept", "John", 11, 35),
    ],
)
def test_text_criterion_fulltext(client, value, book, chapter, verse):
    """A text criterion that isn't a verse reference falls back to full-text search."""
    response = _post(client, [{"type": "text", "value": value}])
    assert response.status_code == 200
    verses = response.json()["verses"]
    assert any(
        v["book"] == book and v["chapter"] == chapter and v["verse"] == verse
        for v in verses
    )


def test_english_criterion_returns_fulltext_hits(client):
    """The english criterion performs a full-text search and returns matching verses."""
    response = _post(client, [{"type": "english", "value": "love"}])
    assert response.status_code == 200
    out = response.json()
    assert out["total"] > 0
    assert all("text" in v for v in out["verses"])


def test_book_only_returns_first_page_of_book(client):
    """A lone book criterion returns the book's verses starting from chapter 1, verse 1."""
    response = _post(client, [{"type": "book", "value": "John"}], query="limit=10")
    assert response.status_code == 200
    out = response.json()
    assert out["total"] > 10
    assert len(out["verses"]) == 10
    assert all(v["book"] == "John" for v in out["verses"])
    assert out["verses"][0]["chapter"] == 1
    assert out["verses"][0]["verse"] == 1


def test_testament_only_starts_at_genesis(client):
    """A lone Old Testament criterion returns verses beginning at Genesis 1:1."""
    response = _post(client, [{"type": "testament", "value": "old"}], query="limit=5")
    assert response.status_code == 200
    out = response.json()
    assert out["total"] > 5
    assert out["verses"][0]["book"] == "Genesis"
    assert out["verses"][0]["chapter"] == 1
    assert out["verses"][0]["verse"] == 1


def test_combined_producer_and_restrictor(client):
    """A book restrictor combined with a text producer filters results to that book."""
    response = _post(
        client,
        [
            {"type": "text", "value": "love"},
            {"type": "book", "value": "John"},
        ],
    )
    assert response.status_code == 200
    out = response.json()
    assert out["total"] > 0
    assert all(v["book"] == "John" for v in out["verses"])


def test_pagination_advances_through_results(client):
    """Requesting page 2 yields a different slice of verses than page 1 with the same total."""
    page1 = _post(client, [{"type": "book", "value": "John"}], query="page=1&limit=5")
    page2 = _post(client, [{"type": "book", "value": "John"}], query="page=2&limit=5")
    assert page1.status_code == 200
    assert page2.status_code == 200
    p1 = page1.json()
    p2 = page2.json()
    assert p1["total"] == p2["total"]
    assert len(p1["verses"]) == 5
    assert len(p2["verses"]) == 5
    assert p1["verses"][0] != p2["verses"][0]


def test_ignored_only_returns_empty(client):
    """A criterion that produces no verses on its own (e.g. author) yields an empty result."""
    response = _post(client, [{"type": "author", "value": "Paul"}])
    assert response.status_code == 200
    assert response.json() == {"total": 0, "verses": []}


def test_ignored_alongside_producer_does_not_affect_results(client):
    """A non-producing, non-restricting criterion alongside a producer leaves it unchanged."""
    base = _post(client, [{"type": "text", "value": "Jesus wept"}])
    mixed = _post(
        client,
        [
            {"type": "text", "value": "Jesus wept"},
            {"type": "author", "value": "Paul"},
        ],
    )
    assert base.status_code == 200
    assert mixed.status_code == 200
    assert base.json() == mixed.json()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "criterion_type,concord_id,expected_refs",
    [
        (
            "hebrew",
            "H0001",
            {("Genesis", 2, 24), ("Genesis", 17, 4), ("Exodus", 20, 12)},
        ),
        ("greek", "G0001", {("Revelation", 1, 8), ("Revelation", 22, 13)}),
    ],
)
def test_concord_producer_returns_mapped_verses(
    client, criterion_type, concord_id, expected_refs
):
    """A hebrew/greek criterion returns every verse mapped to its concordance ID."""
    response = _post(
        client,
        [{"type": criterion_type, "value": "x", "concordance_id": concord_id}],
    )
    assert response.status_code == 200
    out = response.json()
    assert out["total"] == len(expected_refs)
    assert {
        (v["book"], v["chapter"], v["verse"]) for v in out["verses"]
    } == expected_refs


@pytest.mark.django_db
@pytest.mark.parametrize(
    "producer,restrictor,expected_total",
    [
        # H0001 has 3 OT mappings; 2 in Genesis, 1 in Exodus.
        (
            {"type": "hebrew", "concordance_id": "H0001"},
            {"type": "book", "value": "Genesis"},
            2,
        ),
        # Hebrew concords are OT-only — testament=new restricts to nothing.
        (
            {"type": "hebrew", "concordance_id": "H0001"},
            {"type": "testament", "value": "new"},
            0,
        ),
        # Greek concords are NT-only — testament=old restricts to nothing.
        (
            {"type": "greek", "concordance_id": "G0001"},
            {"type": "testament", "value": "old"},
            0,
        ),
        # G0001 has 2 mappings, both in Revelation (NT).
        (
            {"type": "greek", "concordance_id": "G0001"},
            {"type": "testament", "value": "new"},
            2,
        ),
    ],
)
def test_concord_producer_with_restrictor(client, producer, restrictor, expected_total):
    """A hebrew/greek producer AND'd with a book/testament restrictor narrows correctly."""
    response = _post(client, [{**producer, "value": "x"}, restrictor])
    assert response.status_code == 200
    assert response.json()["total"] == expected_total


@pytest.mark.django_db
@pytest.mark.parametrize(
    "concord_id,expected_total",
    [
        ("H0001", 3),  # canonical
        ("h0001", 3),  # lowercase prefix
        ("H1", 3),  # unpadded
        ("h1", 3),  # lowercase + unpadded
        ("H9999", 0),  # well-formed but no mappings
        ("notanid", 0),  # malformed → normalize_concord_id returns None
    ],
)
def test_hebrew_concordance_id_resolution(client, concord_id, expected_total):
    """Hebrew IDs are normalized; unmapped or malformed IDs yield an empty result set."""
    response = _post(
        client, [{"type": "hebrew", "value": "x", "concordance_id": concord_id}]
    )
    assert response.status_code == 200
    assert response.json()["total"] == expected_total


@pytest.mark.django_db
def test_two_concord_producers_intersect(client):
    """Two concord producers AND'd together return only verses tagged with both."""
    response = _post(
        client,
        [
            {"type": "hebrew", "value": "x", "concordance_id": "H0001"},
            {"type": "hebrew", "value": "x", "concordance_id": "H0734"},
        ],
    )
    assert response.status_code == 200
    # H0001 hits Genesis/Exodus; H0734 hits Psalms — disjoint, intersection empty.
    assert response.json() == {"total": 0, "verses": []}


@pytest.mark.parametrize(
    "value",
    ["Luke 0:28", "Luke 100:28", "Luke -1:28", "Luke 1:-1", "Luke 1:110"],
)
def test_out_of_range_verse_refs_return_empty(client, value):
    """Verse references outside the book's chapter/verse range return an empty result set."""
    response = _post(client, [{"type": "text", "value": value}])
    assert response.status_code == 200
    assert response.json()["verses"] == []


@pytest.mark.parametrize(
    "body",
    [
        {},  # criteria missing
        {"criteria": []},  # empty list
        {"criteria": [{"type": "unknown", "value": "x"}]},
        {"criteria": [{"type": "text"}]},  # missing value
        {"criteria": [{"type": "book", "value": "Notabook"}]},
        {"criteria": [{"type": "hebrew", "value": "ab"}]},  # missing concordance_id
    ],
)
def test_bad_payload_returns_400(client, body):
    """Malformed or unrecognized criteria payloads are rejected with HTTP 400."""
    response = client.post(
        reverse("search"),
        data=json.dumps(body),
        content_type="application/json",
    )
    assert response.status_code == 400


def test_invalid_json_returns_400(client):
    """A request body that isn't valid JSON is rejected with HTTP 400."""
    response = client.post(
        reverse("search"),
        data="not-json",
        content_type="application/json",
    )
    assert response.status_code == 400


def test_get_method_not_allowed(client):
    """The search endpoint accepts POST only; GET returns HTTP 405."""
    response = client.get(reverse("search"))
    assert response.status_code == 405
