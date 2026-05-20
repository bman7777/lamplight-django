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
