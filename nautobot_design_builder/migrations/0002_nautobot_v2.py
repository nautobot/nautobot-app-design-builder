# Generated by Django 3.2.25 on 2024-05-03 11:48

from django.db import migrations, models
import django.db.models.deletion
import nautobot.core.models.fields
import nautobot.extras.models.statuses


class Migration(migrations.Migration):

    dependencies = [
        ('extras', '0106_populate_default_statuses_and_roles_for_contact_associations'),
        ('nautobot_design_builder', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='design',
            name='created',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AlterField(
            model_name='design',
            name='tags',
            field=nautobot.core.models.fields.TagsField(through='extras.TaggedItem', to='extras.Tag'),
        ),
        migrations.AlterField(
            model_name='designinstance',
            name='created',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AlterField(
            model_name='designinstance',
            name='last_implemented',
            field=models.DateTimeField(auto_now=True, null=True),
        ),
        migrations.AlterField(
            model_name='designinstance',
            name='live_state',
            field=nautobot.extras.models.statuses.StatusField(default=0, on_delete=django.db.models.deletion.PROTECT, related_name='live_state_status', to='extras.status'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='designinstance',
            name='status',
            field=nautobot.extras.models.statuses.StatusField(default=0, on_delete=django.db.models.deletion.PROTECT, related_name='design_instance_statuses', to='extras.status'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='designinstance',
            name='tags',
            field=nautobot.core.models.fields.TagsField(through='extras.TaggedItem', to='extras.Tag'),
        ),
        migrations.AlterField(
            model_name='journal',
            name='created',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AlterField(
            model_name='journal',
            name='job_result',
            field=models.ForeignKey(editable=False, on_delete=django.db.models.deletion.PROTECT, to='extras.jobresult', unique=True),
        ),
        migrations.AlterField(
            model_name='journal',
            name='tags',
            field=nautobot.core.models.fields.TagsField(through='extras.TaggedItem', to='extras.Tag'),
        ),
    ]
