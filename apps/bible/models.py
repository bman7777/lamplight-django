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
