"""Root-level smoke test that exercises the apps.bible search endpoint."""

from urllib.parse import urlencode

import pytest
from django.urls import reverse


@pytest.mark.parametrize(
    "query,book,chapter,verse",
    [
        ("John 3:16", "John", 3, 16),
        ("Jesus wept", "John", 11, 35),
    ],
)
def test_bible_search_request(client, query, book, chapter, verse):
    response = client.get(f'{reverse("search")}?{urlencode({"q": query})}')

    assert response.status_code == 200
    payload = response.json()["data"][0]
    assert payload["book"] == book
    assert payload["chapter"] == chapter
    assert payload["verse"] == verse
    assert payload["text"]
