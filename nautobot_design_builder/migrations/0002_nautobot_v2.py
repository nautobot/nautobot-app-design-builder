# Generated by Django 3.2.25 on 2024-05-29 14:15

from django.db import migrations, models
import django.db.models.deletion
import nautobot.core.models.fields
import nautobot.extras.models.statuses


class Migration(migrations.Migration):

    dependencies = [
        ("extras", "0106_populate_default_statuses_and_roles_for_contact_associations"),
        ("nautobot_design_builder", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="changeset",
            name="created",
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AlterField(
            model_name="changeset",
            name="tags",
            field=nautobot.core.models.fields.TagsField(through="extras.TaggedItem", to="extras.Tag"),
        ),
        migrations.AlterField(
            model_name="deployment",
            name="created",
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AlterField(
            model_name="deployment",
            name="status",
            field=nautobot.extras.models.statuses.StatusField(
                on_delete=django.db.models.deletion.PROTECT, related_name="deployment_statuses", to="extras.status"
            ),
        ),
        migrations.AlterField(
            model_name="deployment",
            name="tags",
            field=nautobot.core.models.fields.TagsField(through="extras.TaggedItem", to="extras.Tag"),
        ),
        migrations.AlterField(
            model_name="design",
            name="created",
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AlterField(
            model_name="design",
            name="tags",
            field=nautobot.core.models.fields.TagsField(through="extras.TaggedItem", to="extras.Tag"),
        ),
    ]
