"""Replace the denormalized version/book/chapter/verse fields on
ConcordanceVerseMapping with a single FK to Verse.

The mapping table is truncated as part of the migration — it's regenerable
in one command: `./manage.py concordance_map_verses`.
"""

import django.db.models.deletion
from django.db import migrations, models


def _truncate(apps, schema_editor):
    apps.get_model("bible", "ConcordanceVerseMapping").objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("bible", "0007_versespeakermapping_verse_fk"),
    ]

    operations = [
        migrations.RunPython(_truncate, reverse_code=migrations.RunPython.noop),
        migrations.RemoveConstraint(
            model_name="concordanceversemapping",
            name="unique_concord_per_verse",
        ),
        migrations.RemoveIndex(
            model_name="concordanceversemapping",
            name="bible_conco_version_7affdf_idx",
        ),
        migrations.RemoveField(model_name="concordanceversemapping", name="version"),
        migrations.RemoveField(model_name="concordanceversemapping", name="book"),
        migrations.RemoveField(model_name="concordanceversemapping", name="chapter"),
        migrations.RemoveField(model_name="concordanceversemapping", name="verse"),
        migrations.AddField(
            model_name="concordanceversemapping",
            name="verse",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="concord_mappings",
                to="bible.verse",
            ),
        ),
        migrations.AddConstraint(
            model_name="concordanceversemapping",
            constraint=models.UniqueConstraint(
                fields=("concord", "verse"), name="unique_concord_per_verse"
            ),
        ),
    ]
