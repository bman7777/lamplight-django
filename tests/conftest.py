"""Shared pytest fixtures."""

import pytest

from apps.bible.models import (ConcordanceEntry, ConcordanceVerseMapping,
                               Speaker, Verse, VerseSpeakerMapping)


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
        # Verse rows for every mapping below — the FK requires them to exist.
        verse_specs = [
            ("gen", 2, 24),
            ("gen", 17, 4),
            ("exo", 20, 12),
            ("psa", 27, 11),
            ("rev", 1, 8),
            ("rev", 22, 13),
        ]
        verse_by_ref = {}
        for book, chapter, verse in verse_specs:
            pk_id = f"nasb95:{book}:{chapter}:{verse}"
            obj, _ = Verse.objects.get_or_create(
                pk_id=pk_id,
                defaults={
                    "version": "nasb95",
                    "book": book,
                    "chapter": chapter,
                    "verse": verse,
                    "text": "",
                    "sort_order": 0,
                },
            )
            verse_by_ref[(book, chapter, verse)] = obj

        ConcordanceVerseMapping.objects.bulk_create(
            [
                # H0001 ("ab"/father) — three OT verses, two in Genesis, one in Exodus
                ConcordanceVerseMapping(
                    concord_id="H0001", verse=verse_by_ref[("gen", 2, 24)]
                ),
                ConcordanceVerseMapping(
                    concord_id="H0001", verse=verse_by_ref[("gen", 17, 4)]
                ),
                ConcordanceVerseMapping(
                    concord_id="H0001", verse=verse_by_ref[("exo", 20, 12)]
                ),
                # H0734 ("'orach"/way) — one OT verse, lets us test single-hit lookups
                ConcordanceVerseMapping(
                    concord_id="H0734", verse=verse_by_ref[("psa", 27, 11)]
                ),
                # G0001 ("alpha") — NT verses in Revelation
                ConcordanceVerseMapping(
                    concord_id="G0001", verse=verse_by_ref[("rev", 1, 8)]
                ),
                ConcordanceVerseMapping(
                    concord_id="G0001", verse=verse_by_ref[("rev", 22, 13)]
                ),
            ]
        )
        # Seed a couple of speakers for the speaker-criterion tests.
        jesus = Speaker.objects.create(name="Jesus")
        Speaker.objects.create(name="God")
        mat_5_3, _ = Verse.objects.get_or_create(
            pk_id="nasb95:mat:5:3",
            defaults={"version": "nasb95", "book": "mat", "chapter": 5, "verse": 3, "text": "", "sort_order": 0},
        )
        jhn_3_3, _ = Verse.objects.get_or_create(
            pk_id="nasb95:jhn:3:3",
            defaults={"version": "nasb95", "book": "jhn", "chapter": 3, "verse": 3, "text": "", "sort_order": 0},
        )
        VerseSpeakerMapping.objects.bulk_create(
            [
                VerseSpeakerMapping(speaker=jesus, verse=mat_5_3),
                VerseSpeakerMapping(speaker=jesus, verse=jhn_3_3),
            ]
        )
