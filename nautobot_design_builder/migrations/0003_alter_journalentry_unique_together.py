# Generated by Django 3.2.25 on 2024-05-03 18:33

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('nautobot_design_builder', '0002_nautobot_v2'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='journalentry',
            unique_together={('journal', 'index')},
        ),
    ]