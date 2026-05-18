"""Haystack search index for Bible verses.

Verses are seeded by the bible_to_haystack management command, which feeds
in-memory Verse objects (built from apps/bible/data/bible.json) directly to
the Whoosh backend. There is no DB-backed queryset to iterate, so
index_queryset() returns an empty queryset — update_index would do nothing.
"""

from haystack import indexes

from .models import Verse


class VerseIndex(indexes.SearchIndex, indexes.Indexable):
    """Whoosh schema for the Verse model; populated by bible_to_haystack."""

    text = indexes.CharField(document=True, use_template=False, model_attr="text")
    version = indexes.CharField(model_attr="version", faceted=True)
    book = indexes.CharField(model_attr="book", faceted=True)
    chapter = indexes.IntegerField(model_attr="chapter")
    verse = indexes.IntegerField(model_attr="verse")

    def get_model(self):
        return Verse

    def index_queryset(self, using=None):
        # pylint: disable=no-member  # Django attaches `objects` dynamically.
        return Verse.objects.none()
