"""Shared pytest fixtures."""

import pytest

from apps.bible.models import ConcordanceEntry, ConcordanceVerseMapping


@pytest.fixture(scope="session")
def django_db_setup(
    django_db_setup, django_db_blocker
):  # pylint: disable=redefined-outer-name,unused-argument
    """Seed a handful of concordance entries once per session for endpoint tests."""

    with django_db_blocker.unblock():
        ConcordanceEntry.objects.bulk_create(
            [
                ConcordanceEntry(
                    concord_id="G0001",
                    original_word="ἄλφα",
                    transliteration="alpha",
                    part_of_speech="indeclinable noun",
                    english_translations=[{"translation": "Alpha", "count": 4}],
                    outline_definitions=["first letter of Greek alphabet"],
                    strongs_definition=["†Α A, al'-fah"],
                ),
                ConcordanceEntry(
                    concord_id="H0001",
                    original_word="אָב",
                    transliteration="ab",
                    part_of_speech="noun masculine",
                    english_translations=[{"translation": "father", "count": 1}],
                    outline_definitions=["father of an individual"],
                    strongs_definition=["אָב 'âb"],
                ),
                ConcordanceEntry(
                    concord_id="H0734",
                    original_word="אֹרַח",
                    transliteration="ʼôrach",
                    part_of_speech="noun masculine",
                    english_translations=[{"translation": "way", "count": 1}],
                    outline_definitions=["way, path"],
                    strongs_definition=["אֹרַח 'ôrach"],
                ),
            ]
        )
        ConcordanceVerseMapping.objects.bulk_create(
            [
                # H0001 ("ab"/father) — three OT verses, two in Genesis, one in Exodus
                ConcordanceVerseMapping(
                    concord_id="H0001",
                    version="nasb95",
                    book="gen",
                    chapter=2,
                    verse=24,
                ),
                ConcordanceVerseMapping(
                    concord_id="H0001",
                    version="nasb95",
                    book="gen",
                    chapter=17,
                    verse=4,
                ),
                ConcordanceVerseMapping(
                    concord_id="H0001",
                    version="nasb95",
                    book="exo",
                    chapter=20,
                    verse=12,
                ),
                # H0734 ("'orach"/way) — one OT verse, lets us test single-hit lookups
                ConcordanceVerseMapping(
                    concord_id="H0734",
                    version="nasb95",
                    book="psa",
                    chapter=27,
                    verse=11,
                ),
                # G0001 ("alpha") — NT verses in Revelation
                ConcordanceVerseMapping(
                    concord_id="G0001", version="nasb95", book="rev", chapter=1, verse=8
                ),
                ConcordanceVerseMapping(
                    concord_id="G0001",
                    version="nasb95",
                    book="rev",
                    chapter=22,
                    verse=13,
                ),
            ]
        )
