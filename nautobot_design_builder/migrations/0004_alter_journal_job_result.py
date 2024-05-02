# Generated by Django 3.2.25 on 2024-05-03 18:39

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('extras', '0106_populate_default_statuses_and_roles_for_contact_associations'),
        ('nautobot_design_builder', '0003_alter_journalentry_unique_together'),
    ]

    operations = [
        migrations.AlterField(
            model_name='journal',
            name='job_result',
            field=models.OneToOneField(editable=False, on_delete=django.db.models.deletion.PROTECT, to='extras.jobresult'),
        ),
    ]
