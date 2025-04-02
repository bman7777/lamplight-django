import json
from urllib.parse import urlencode

import pytest
from django.test import Client, TestCase
from django.urls import reverse


@pytest.mark.parametrize(
    "text_input",
    [
        ("Romans 8:28", "Romans", 8, 28),
        ("Romans 8", "Romans", 8),
        ("Rom",),
        ("Romans",),
        ("1 John 3:16", "1 John", 3, 16),
        ("song of songs 1:22", "Song Of Songs", 1, 22),
        ("1JOhn 3:16", "1 John", 3, 16),
        ("love",),
        ("for God so loved",),
    ],
)
def test_standard_query_strings(text_input, client):
    """Test good input search strings."""

    # search with the given text input
    query_params = {"q": text_input[0]}
    response = client.post(f'{reverse("search")}?{urlencode(query_params)}')
    assert response.status_code == 201

    out = response.json()
    if len(text_input) > 1:
        assert out["data"][0]["book"] == text_input[1]
    if len(text_input) > 2:
        assert out["data"][0]["chapter"] == text_input[2]
    if len(text_input) > 3:
        assert out["data"][0]["verse"] == text_input[3]
    assert out["data"][0]["text"]
