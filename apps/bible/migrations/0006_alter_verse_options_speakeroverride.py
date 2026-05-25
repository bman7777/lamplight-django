"""Promote Verse to a managed table and add the SpeakerOverride model.

Verse was originally created with managed=False (verses lived only in Redis +
Whoosh), so its table was never created. We now want a real Verse table so the
admin can browse every verse and attach a SpeakerOverride (a per-verse manual
speaker assignment that supersedes the extractor's guesses in speaker.json).
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("bible", "0005_speaker_versespeakermapping"),
    ]

    operations = [
        # State: Verse is now managed (so subsequent makemigrations behave) and
        # gains sort_order + indexes. DB: actually create the table, since
        # 0001_initial was a no-op for Verse (managed=False).
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterModelOptions(
                    name="verse",
                    options={"ordering": ["sort_order"]},
                ),
                migrations.AddField(
                    model_name="verse",
                    name="sort_order",
                    field=models.IntegerField(default=0),
                ),
                migrations.AddIndex(
                    model_name="verse",
                    index=models.Index(
                        fields=["version", "book", "chapter", "verse"],
                        name="bible_verse_vbcv_idx",
                    ),
                ),
                migrations.AddIndex(
                    model_name="verse",
                    index=models.Index(
                        fields=["sort_order"], name="bible_verse_sort_idx"
                    ),
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql=(
                        "CREATE TABLE bible_verse ("
                        "pk_id varchar(64) NOT NULL PRIMARY KEY, "
                        "version varchar(16) NOT NULL, "
                        "book varchar(8) NOT NULL, "
                        "chapter integer NOT NULL, "
                        "verse integer NOT NULL, "
                        '"text" text NOT NULL, '
                        "sort_order integer NOT NULL DEFAULT 0"
                        ");"
                    ),
                    reverse_sql="DROP TABLE bible_verse;",
                ),
                migrations.RunSQL(
                    sql=(
                        "CREATE INDEX bible_verse_vbcv_idx "
                        "ON bible_verse (version, book, chapter, verse);"
                    ),
                    reverse_sql="DROP INDEX bible_verse_vbcv_idx;",
                ),
                migrations.RunSQL(
                    sql=(
                        "CREATE INDEX bible_verse_sort_idx "
                        "ON bible_verse (sort_order);"
                    ),
                    reverse_sql="DROP INDEX bible_verse_sort_idx;",
                ),
            ],
        ),
        migrations.CreateModel(
            name="SpeakerOverride",
            fields=[
                (
                    "verse",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        primary_key=True,
                        related_name="speaker_override",
                        serialize=False,
                        to="bible.verse",
                    ),
                ),
                (
                    "speakers",
                    models.ManyToManyField(
                        blank=True, related_name="overrides", to="bible.speaker"
                    ),
                ),
            ],
        ),
    ]
