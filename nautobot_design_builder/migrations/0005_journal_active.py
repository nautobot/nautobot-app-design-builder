# Generated by Django 3.2.23 on 2024-01-22 08:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('nautobot_design_builder', '0004_journal_builder_output'),
    ]

    operations = [
        migrations.AddField(
            model_name='journal',
            name='active',
            field=models.BooleanField(default=True, editable=False),
        ),
    ]