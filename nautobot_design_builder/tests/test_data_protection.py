"""Test Data Protection features."""

import copy
from django.test import Client, override_settings
from django.conf import settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType

from nautobot.dcim.models import Manufacturer
from nautobot.extras.plugins import register_custom_validators
from nautobot.users.models import ObjectPermission

from nautobot_design_builder.design import calculate_changes
from .test_model_design_instance import BaseDesignInstanceTest
from ..models import JournalEntry
from ..custom_validators import custom_validators
from ..signals import load_pre_delete_signals

User = get_user_model()
plugin_settings_with_defaults = copy.deepcopy(settings.PLUGINS_CONFIG)
plugin_settings_with_defaults["nautobot_design_builder"]["protected_models"] = []
plugin_settings_with_defaults["nautobot_design_builder"]["protected_superuser_bypass"] = True

plugin_settings_with_protection = copy.deepcopy(plugin_settings_with_defaults)
plugin_settings_with_protection["nautobot_design_builder"]["protected_models"] = [("dcim", "manufacturer")]

plugin_settings_with_protection_and_superuser_bypass_disabled = copy.deepcopy(plugin_settings_with_protection)
plugin_settings_with_protection_and_superuser_bypass_disabled["nautobot_design_builder"][
    "protected_superuser_bypass"
] = False


class DataProtectionBaseTest(BaseDesignInstanceTest):  # pylint: disable=too-many-instance-attributes
    """Data Protection Test."""

    def setUp(self):
        super().setUp()
        self.original_name = "original equipment manufacturer"
        self.manufacturer_from_design = Manufacturer.objects.create(name=self.original_name, description="something")
        self.job_kwargs = {
            "manufacturer": f"{self.manufacturer_from_design.pk}",
            "instance": "my instance",
        }

        self.journal = self.create_journal(self.job1, self.design_instance, self.job_kwargs)
        self.initial_entry = JournalEntry.objects.create(
            design_object=self.manufacturer_from_design,
            full_control=True,
            changes=calculate_changes(self.manufacturer_from_design),
            journal=self.journal,
        )

        self.client = Client()

        self.user = User.objects.create_user(username="test_user", email="test@example.com", password="password123")
        self.admin = User.objects.create_user(
            username="test_user_admin", email="admin@example.com", password="password123", is_superuser=True
        )

        actions = ["view", "add", "change", "delete"]
        permission, _ = ObjectPermission.objects.update_or_create(
            name="dcim-manufacturer-test",
            defaults={"constraints": {}, "actions": actions},
        )
        permission.validated_save()
        permission.object_types.set([ContentType.objects.get(app_label="dcim", model="manufacturer")])
        permission.users.set([self.user])


class DataProtectionBaseTestWithDefaults(DataProtectionBaseTest):
    """Test for Data Protection with defaults."""

    @override_settings(PLUGINS_CONFIG=plugin_settings_with_defaults)
    def test_update_as_user_without_protection(self):
        register_custom_validators(custom_validators)
        self.client.login(username="test_user", password="password123")
        response = self.client.patch(
            reverse("dcim-api:manufacturer-detail", kwargs={"pk": self.manufacturer_from_design.pk}),
            data={"description": "new description"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

    @override_settings(PLUGINS_CONFIG=plugin_settings_with_defaults)
    def test_delete_as_user_without_protection(self):
        load_pre_delete_signals()
        self.client.login(username="test_user", password="password123")
        response = self.client.delete(
            reverse("dcim-api:manufacturer-detail", kwargs={"pk": self.manufacturer_from_design.pk}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 204)


class DataProtectionBaseTestWithProtection(DataProtectionBaseTest):
    """Test for Data Protection with protected objects."""

    @override_settings(PLUGINS_CONFIG=plugin_settings_with_protection)
    def test_update_as_user_with_protection(self):
        register_custom_validators(custom_validators)
        self.client.login(username="test_user", password="password123")
        response = self.client.patch(
            reverse("dcim-api:manufacturer-detail", kwargs={"pk": self.manufacturer_from_design.pk}),
            data={"description": "new description"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["description"][0],
            f"The attribute is managed by the Design Instance. {self.design_instance}. ",
        )

    # TODO: bypass protection is not ready for update yet
    @override_settings(PLUGINS_CONFIG=plugin_settings_with_protection)
    def test_update_as_admin_with_protection_and_with_bypass(self):
        register_custom_validators(custom_validators)
        self.client.login(username="test_user_admin", password="password123")
        response = self.client.patch(
            reverse("dcim-api:manufacturer-detail", kwargs={"pk": self.manufacturer_from_design.pk}),
            data={"description": "new description"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)

    @override_settings(PLUGINS_CONFIG=plugin_settings_with_protection)
    def test_delete_as_user_with_protection(self):
        load_pre_delete_signals()
        self.client.login(username="test_user", password="password123")
        response = self.client.delete(
            reverse("dcim-api:manufacturer-detail", kwargs={"pk": self.manufacturer_from_design.pk}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 409)
        # self.assertEqual(
        #     response.json()["description"][0],
        #     f"The attribute is managed by the Design Instance. {self.design_instance}: ",
        # )

    @override_settings(PLUGINS_CONFIG=plugin_settings_with_protection)
    def test_delete_as_admin_with_protection_and_with_bypass(self):
        load_pre_delete_signals()
        self.client.login(username="test_user_admin", password="password123")
        response = self.client.delete(
            reverse("dcim-api:manufacturer-detail", kwargs={"pk": self.manufacturer_from_design.pk}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 204)


class DataProtectionBaseTestWithProtectionBypassDisabled(DataProtectionBaseTest):
    """Test for Data Protection with data protection by superuser bypass."""

    @override_settings(PLUGINS_CONFIG=plugin_settings_with_protection_and_superuser_bypass_disabled)
    def test_update_as_admin_with_protection_and_without_bypass(self):
        register_custom_validators(custom_validators)
        self.client.login(username="test_user_admin", password="password123")
        response = self.client.patch(
            reverse("dcim-api:manufacturer-detail", kwargs={"pk": self.manufacturer_from_design.pk}),
            data={"description": "new description"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["description"][0],
            f"The attribute is managed by the Design Instance: {self.design_instance}: ",
        )

    @override_settings(PLUGINS_CONFIG=plugin_settings_with_protection_and_superuser_bypass_disabled)
    def test_delete_as_admin_with_protection_and_without_bypass(self):
        load_pre_delete_signals()
        self.client.login(username="test_user_admin", password="password123")
        response = self.client.delete(
            reverse("dcim-api:manufacturer-detail", kwargs={"pk": self.manufacturer_from_design.pk}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 409)
        # self.assertEqual(
        #     response.json()["description"][0],
        #     f"The attribute is managed by the Design Instance. {self.design_instance}: ",
        # )
