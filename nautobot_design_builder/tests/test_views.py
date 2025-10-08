"""Test Views."""

import re

from django.contrib.contenttypes.models import ContentType
from django.test import override_settings
from django.test.testcases import assert_and_parse_html
from django.utils.html import format_html
from nautobot.apps.testing import ViewTestCases
from nautobot.core.templatetags import buttons, helpers
from nautobot.core.testing import utils
from nautobot.users import models as users_models

from nautobot_design_builder.models import ChangeRecord, ChangeSet, Deployment, Design
from nautobot_design_builder.tests.util import create_test_view_data

# pylint: disable=missing-class-docstring


class TestCaseDesign(
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.GetObjectChangelogViewTestCase,
    ViewTestCases.GetObjectNotesViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
):
    model = Design

    @classmethod
    def setUpTestData(cls):
        create_test_view_data()


class TestCaseDeployment(
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.GetObjectChangelogViewTestCase,
    ViewTestCases.GetObjectNotesViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
):
    model = Deployment

    @classmethod
    def setUpTestData(cls):
        create_test_view_data()


class TestCaseChangeSet(
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.GetObjectChangelogViewTestCase,
    ViewTestCases.GetObjectNotesViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
):
    model = ChangeSet

    @classmethod
    def setUpTestData(cls):
        create_test_view_data()


class TestCaseChangeRecord(
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.GetObjectChangelogViewTestCase,
    ViewTestCases.GetObjectNotesViewTestCase,
):
    model = ChangeRecord

    @classmethod
    def setUpTestData(cls):
        create_test_view_data()

    # TODO: Remove this entire method when we change to using DateTimeField for `created` field on ChangeRecord model.
    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    def test_has_timestamps_and_buttons(self):  # pylint: disable=too-many-locals
        instance = self._get_queryset().first()

        # Add model-level permission
        obj_perm = users_models.ObjectPermission(name="Test permission", actions=["view", "add", "change", "delete"])
        obj_perm.save()
        obj_perm.users.add(self.user)
        obj_perm.object_types.add(ContentType.objects.get_for_model(self.model))

        response = self.client.get(instance.get_absolute_url())

        # if hasattr(instance, "created") and hasattr(instance, "last_updated"):
        #     self.assertBodyContains(response, date(instance.created, global_settings.DATETIME_FORMAT), html=True)
        # We don't assert the rendering of `last_updated` because it's relative time ("10 minutes ago") and
        # therefore is subject to off-by-one timing failures.

        object_edit_url = buttons.edit_button(instance)["url"]
        object_delete_url = buttons.delete_button(instance)["url"]
        object_clone_url = buttons.clone_button(instance)["url"]
        render_edit_button = bool(object_edit_url)
        render_delete_button = bool(object_delete_url)
        render_clone_button = bool(hasattr(instance, "clone_fields") and object_clone_url)
        action_buttons = []
        if render_edit_button:
            action_buttons.append(
                format_html(
                    """
                        <a id="edit-button" class="btn btn-warning" href="{}">
                            <span class="mdi mdi-pencil" aria-hidden="true"></span> Edit {}
                        </a>
                    """,
                    object_edit_url,
                    helpers.bettertitle(self.model._meta.verbose_name),
                )
            )
        if render_delete_button:
            action_buttons.append(
                format_html(
                    """
                        <a id="delete-button" class="dropdown-item text-danger" href="{}">
                            <span class="mdi mdi-trash-can-outline" aria-hidden="true"></span> Delete {}
                        </a>
                    """,
                    object_delete_url,
                    helpers.bettertitle(self.model._meta.verbose_name),
                )
            )
        if render_clone_button:
            action_buttons.append(
                format_html(
                    """
                        <a id="clone-button" class="dropdown-item" href="{}">
                            <span class="mdi mdi-plus-thick text-secondary" aria-hidden="true"></span> Clone {}
                        </a>
                    """,
                    object_clone_url,
                    helpers.bettertitle(self.model._meta.verbose_name),
                )
            )

        # Because we are looking for a hypothetical use of legacy button templates on the page here, we need some
        # additional logic to know if this assertion should be made in the first place, and be handled in the `if`
        # below, or fall back to standard button presence check in the `else` case otherwise.
        content = assert_and_parse_html(
            self,
            utils.extract_page_body(response.content.decode(response.charset)),
            None,
            "Response's content is not valid HTML:",
        )
        for button in action_buttons:
            button_parsed = assert_and_parse_html(self, button, None, "Button is not valid HTML:")
            button_id_attribute = re.search(r"id=\"([A-Za-z]+[\w\-\:\.]*)\"", button).group(0)
            real_count = content.count(button_parsed)
            if (real_count is None or real_count == 0) and button_id_attribute in str(content):
                self.fail(
                    f"Couldn't find {button} in response, but an element with `{button_id_attribute}` has been found. Is the page using legacy button template?\n{content}",
                )
            else:
                # If it wasn't for the legacy button template check above, this would be the only thing needed here.
                self.assertBodyContains(response, button, html=True)
