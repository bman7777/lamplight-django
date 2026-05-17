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

    class Meta:
        managed = False
        app_label = "bible"
