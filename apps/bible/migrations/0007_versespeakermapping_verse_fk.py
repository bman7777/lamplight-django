"""Replace the denormalized version/book/chapter/verse fields on
VerseSpeakerMapping with a single FK to Verse.

VerseSpeakerMapping was denormalized only because Verse wasn't a real DB
table; now that it is, the FK is the natural model. The mapping table is
truncated as part of the migration — it's regenerable in one command:
`./manage.py speakers_to_db`.
"""

import django.db.models.deletion
from django.db import migrations, models


def _truncate(apps, schema_editor):
    apps.get_model("bible", "VerseSpeakerMapping").objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("bible", "0006_alter_verse_options_speakeroverride"),
    ]

    operations = [
        migrations.RunPython(_truncate, reverse_code=migrations.RunPython.noop),
        migrations.RemoveConstraint(
            model_name="versespeakermapping",
            name="unique_speaker_per_verse",
        ),
        migrations.RemoveIndex(
            model_name="versespeakermapping",
            name="bible_verse_version_45ba3c_idx",
        ),
        migrations.RemoveField(model_name="versespeakermapping", name="version"),
        migrations.RemoveField(model_name="versespeakermapping", name="book"),
        migrations.RemoveField(model_name="versespeakermapping", name="chapter"),
        migrations.RemoveField(model_name="versespeakermapping", name="verse"),
        migrations.AddField(
            model_name="versespeakermapping",
            name="verse",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="speaker_mappings",
                to="bible.verse",
            ),
        ),
        migrations.AddConstraint(
            model_name="versespeakermapping",
            constraint=models.UniqueConstraint(
                fields=("speaker", "verse"), name="unique_speaker_per_verse"
            ),
        ),
    ]
