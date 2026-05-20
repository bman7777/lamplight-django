"""End-to-end tests for the /ll/concordance/<concord_id>/ endpoint."""

import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_concordance_returns_entry(client):
    """A known concord_id returns 200 with the full serialized entry."""

    response = client.get(reverse("concordance", kwargs={"concord_id": "G0001"}))
    assert response.status_code == 200
    assert response.json() == {
        "concord_id": "G0001",
        "original_word": "ἄλφα",
        "transliteration": "alpha",
        "part_of_speech": "indeclinable noun",
        "english_translations": [{"translation": "Alpha", "count": 4}],
        "outline_definitions": ["first letter of Greek alphabet"],
        "strongs_definition": ["†Α A, al'-fah"],
    }


@pytest.mark.django_db
def test_concordance_missing_id_returns_404(client):
    """An unknown concord_id returns 404."""

    response = client.get(reverse("concordance", kwargs={"concord_id": "G9999"}))
    assert response.status_code == 404


@pytest.mark.django_db
@pytest.mark.parametrize(
    "concord_id, expected",
    [
        ("H734", "H0734"),
        ("H1", "H0001"),
        ("h1", "H0001"),
        ("G1", "G0001"),
        ("H0001", "H0001"),
    ],
)
def test_concordance_zero_pads_short_ids(client, concord_id, expected):
    """Short or lowercase IDs are normalized to the canonical 4-digit form."""

    response = client.get(reverse("concordance", kwargs={"concord_id": concord_id}))
    assert response.status_code == 200
    assert response.json()["concord_id"] == expected
