import json
from urllib.parse import urlencode

import pytest
from django.test import Client, TestCase
from django.urls import reverse


@pytest.mark.parametrize(
    "text_input",
    [
        ("Luke 1:28", "Luke", 1, 28),
        ("Luke 1", "Luke", 1),
        ("1 John 3:16", "1 John", 3, 16),
        ("song of songs 1:22", "Song Of Songs", 1, 22),
        ("1JOhn 3:16", "1 John", 3, 16),
        ("inasmuch", "Luke", 1, 1),
        ("priestly", "Luke", 1, 23),
        ("Do not be afraid, Zacharias", "Luke", 1, 13),
    ],
)
def test_standard_query_strings(text_input, client):
    """Test good input search strings."""

    response = client.post(f'{reverse("search")}?{urlencode({"q": text_input[0]})}')
    assert response.status_code == 201

    out = response.json()
    if len(text_input) > 1:
        assert out["data"][0]["book"] == text_input[1]
    if len(text_input) > 2:
        assert out["data"][0]["chapter"] == text_input[2]
    if len(text_input) > 3:
        assert out["data"][0]["verse"] == text_input[3]
    assert out["data"][0]["text"]
