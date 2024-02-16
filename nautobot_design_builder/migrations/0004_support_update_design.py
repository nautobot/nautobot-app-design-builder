# Generated by Django 3.2.20 on 2024-02-15 11:09

from django.db import migrations, models
import nautobot.core.celery


class Migration(migrations.Migration):
    dependencies = [
        ("nautobot_design_builder", "0003_tune_design_models"),
    ]

    operations = [
        migrations.AddField(
            model_name="journal",
            name="active",
            field=models.BooleanField(default=True, editable=False),
        ),
        migrations.AddField(
            model_name="journal",
            name="builder_output",
            field=models.JSONField(
                blank=True, editable=False, encoder=nautobot.core.celery.NautobotKombuJSONEncoder, null=True
            ),
        ),
        migrations.AddField(
            model_name="journalentry",
            name="active",
            field=models.BooleanField(default=True, editable=False),
        ),
        migrations.AlterField(
            model_name="designinstance",
            name="owner",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
    ]