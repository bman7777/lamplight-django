"""Bible models."""

from django.db import models


class Verse(models.Model):
    """In-memory contract for haystack's SearchIndex.

    Not backed by a database table (managed=False). Verse data is sourced from
    apps/bible/data/bible.json and lives in Redis + the Whoosh index, not the ORM.
    """

    pk_id = models.CharField(primary_key=True, max_length=64)
    version = models.CharField(max_length=16)
    book = models.CharField(max_length=8)
    chapter = models.IntegerField()
    verse = models.IntegerField()
    text = models.TextField()

    class Meta:  # pylint: disable=too-few-public-methods
        """Django model metadata."""

        managed = False
        app_label = "bible"


class ConcordanceEntry(models.Model):
    """Strong's concordance entry sourced from apps/bible/data/concordance.json.

    The concord_id prefix encodes the language: 'G' = Greek, 'H' = Hebrew.
    """

    concord_id = models.CharField(primary_key=True, max_length=8)
    original_word = models.TextField()
    transliteration = models.TextField()
    part_of_speech = models.TextField()
    english_translations = models.JSONField(default=list)
    outline_definitions = models.JSONField(default=list)
    strongs_definition = models.JSONField(default=list)

    class Meta:  # pylint: disable=too-few-public-methods
        """Django model metadata."""

        app_label = "bible"
        verbose_name_plural = "concordance entries"

    def __str__(self) -> str:
        return f"{self.concord_id} {self.transliteration}"


class ConcordanceVerseMapping(models.Model):
    """Maps a Strong's concordance entry to a verse it appears in.

    Sourced from the <H####>/<G####> markup in apps/bible/data/bible.csv.
    The verse is denormalized into version/book/chapter/verse fields because
    the Verse model is managed=False (Redis + Whoosh, no DB table).
    """

    concord = models.ForeignKey(
        ConcordanceEntry,
        on_delete=models.CASCADE,
        related_name="verse_mappings",
    )
    version = models.CharField(max_length=16)
    book = models.CharField(max_length=8)
    chapter = models.IntegerField()
    verse = models.IntegerField()

    class Meta:  # pylint: disable=too-few-public-methods
        """Django model metadata."""

        app_label = "bible"
        constraints = [
            models.UniqueConstraint(
                fields=["concord", "version", "book", "chapter", "verse"],
                name="unique_concord_per_verse",
            ),
        ]
        indexes = [
            models.Index(fields=["version", "book", "chapter", "verse"]),
        ]

    def __str__(self) -> str:
        return f"{self.concord_id} @ {self.version}:{self.book}:{self.chapter}:{self.verse}"


class Author(models.Model):
    """Canonical author identity. Looked up by name to resolve author search criteria."""

    name = models.CharField(max_length=64, unique=True)

    class Meta:  # pylint: disable=too-few-public-methods
        """Django model metadata."""

        app_label = "bible"

    def __str__(self) -> str:
        return self.name


class Authorship(models.Model):
    """Author(s) and approximate date of writing for a book or specific chapter.

    book_name stores the short book code (e.g. "gen", "jhn") matching
    apps/bible/data/book_map.json. author is a list of Author.id values.
    A NULL chapter means "the whole book"; a chapter-specific row overrides
    the NULL row for that chapter (used for Psalms where attribution varies).
    """

    book_name = models.CharField(max_length=8)
    chapter = models.IntegerField(null=True, blank=True)
    author = models.JSONField(default=list)
    date = models.IntegerField()
    is_bc = models.BooleanField()

    class Meta:  # pylint: disable=too-few-public-methods
        """Django model metadata."""

        app_label = "bible"
        constraints = [
            models.UniqueConstraint(
                fields=["book_name", "chapter"],
                name="unique_book_chapter_specific",
                condition=models.Q(chapter__isnull=False),
            ),
            models.UniqueConstraint(
                fields=["book_name"],
                name="unique_book_chapter_null",
                condition=models.Q(chapter__isnull=True),
            ),
        ]

    def __str__(self) -> str:
        era = "BC" if self.is_bc else "AD"
        suffix = f":{self.chapter}" if self.chapter is not None else ""
        return f"{self.book_name}{suffix} ({self.date} {era})"


class Speaker(models.Model):
    """A canonical speaker name surfaced by apps/bible/data/speaker.json.

    Verses can have multiple speakers; the relationship lives in
    VerseSpeakerMapping. Names are unique and matched case-insensitively
    by search criteria.
    """

    name = models.CharField(max_length=128, unique=True)

    class Meta:  # pylint: disable=too-few-public-methods
        """Django model metadata."""

        app_label = "bible"

    def __str__(self) -> str:
        return self.name


class VerseSpeakerMapping(models.Model):
    """Maps a Speaker to a verse they speak in.

    Sourced from apps/bible/data/speaker.json. The verse is denormalized
    into version/book/chapter/verse fields because the Verse model is
    managed=False (Redis + Whoosh, no DB table). A verse with multiple
    speakers gets one row per speaker.
    """

    speaker = models.ForeignKey(
        Speaker,
        on_delete=models.CASCADE,
        related_name="verse_mappings",
    )
    version = models.CharField(max_length=16)
    book = models.CharField(max_length=8)
    chapter = models.IntegerField()
    verse = models.IntegerField()

    class Meta:  # pylint: disable=too-few-public-methods
        """Django model metadata."""

        app_label = "bible"
        constraints = [
            models.UniqueConstraint(
                fields=["speaker", "version", "book", "chapter", "verse"],
                name="unique_speaker_per_verse",
            ),
        ]
        indexes = [
            models.Index(fields=["version", "book", "chapter", "verse"]),
        ]

    def __str__(self) -> str:
        return (
            f"{self.speaker_id} @ "
            f"{self.version}:{self.book}:{self.chapter}:{self.verse}"
        )
