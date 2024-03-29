# Generated by Django 3.2.8 on 2021-11-23 19:23

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("contenttypes", "0002_remove_content_type_name"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ObjectHistory",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("session_id", models.UUIDField(editable=False)),
                ("session_date", models.DateTimeField(editable=False)),
                (
                    "change_type",
                    models.CharField(
                        choices=[("I", "Insert"), ("D", "Delete"), ("U", "Update")],
                        editable=False,
                        max_length=1,
                    ),
                ),
                ("object_id", models.BigIntegerField(editable=False)),
                ("snapshot", models.JSONField(blank=True, editable=False, null=True)),
                ("changes", models.JSONField(blank=True, editable=False, null=True)),
                (
                    "content_type",
                    models.ForeignKey(
                        editable=False,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="+",
                        to="contenttypes.contenttype",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        db_constraint=False,
                        editable=False,
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="object_history",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name_plural": "object history",
                "db_table": "object_history",
                "abstract": False,
                "swappable": "HISTORY_MODEL",
                "get_latest_by": ["session_date", "id"],
            },
        ),
        migrations.AddIndex(
            model_name="objecthistory",
            index=models.Index(
                fields=["content_type", "object_id"],
                name="object_hist_content_7d3a2e_idx",
            ),
        ),
    ]
