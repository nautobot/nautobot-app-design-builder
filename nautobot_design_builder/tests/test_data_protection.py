"""Test Data Protection features."""

from contextlib import contextmanager

from django.conf import settings
from django.test import Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType

from nautobot.dcim.models import Manufacturer
from nautobot.extras.plugins import register_custom_validators
from nautobot.extras.registry import registry
from nautobot.users.models import ObjectPermission

from nautobot_design_builder.custom_validators import BaseValidator

from .test_model_deployment import BaseDeploymentTest

User = get_user_model()


@contextmanager
def register_validators(*models):
    """Register a set of validators for testing.

    This context manager will register the design builder custom validator
    for each of the models given. Once registered, the context manager yields
    for the tests to run, and then will remove the custom validators when done.
    """
    validators_registry = registry["plugin_custom_validators"]
    pre_validators = {**validators_registry}
    validators = []
    for app_label, model in models:
        validators.append(BaseValidator.factory(app_label, model))
    register_custom_validators(validators)
    yield
    for validator in validators:
        validator.disconnect()
    post_models = set(validators_registry.keys())
    for model in pre_validators:
        validators_registry[model] = pre_validators[model]
        post_models.remove(model)

    for model in post_models:
        validators_registry.pop(model)


class CustomValidatorTest(BaseDeploymentTest):
    """Test the Design Builder custom validator."""

    def setUp(self):
        super().setUp()
        self.change_set = self.create_change_set(self.job, self.deployment, {})
        self.manufacturer = Manufacturer(
            name="Manufacturer 1",
            description="Manufacturer's description",
        )
        self.manufacturer.validated_save()
        self.change_record = self.create_change_record(
            self.manufacturer,
            changes={
                "name": {
                    "old_value": None,
                    "new_value": self.manufacturer.name,
                },
                "description": {
                    "old_value": None,
                    "new_value": self.manufacturer.description,
                },
            },
            active=True,
            full_control=True,
        )
        self.change_record.validated_save()

        self.client = Client()

        self.password = "password123"
        self.user = User.objects.create_user(username="test_user", email="test@example.com", password=self.password)
        self.admin = User.objects.create_user(
            username="test_user_admin", email="admin@example.com", password=self.password, is_superuser=True
        )

        actions = ["view", "add", "change", "delete"]
        permission, _ = ObjectPermission.objects.update_or_create(
            name="dcim-manufacturer-test",
            defaults={"constraints": {}, "actions": actions},
        )
        permission.validated_save()
        permission.object_types.set([ContentType.objects.get(app_label="dcim", model="manufacturer")])
        permission.users.set([self.user])

    def _patch(self, user, *validators, **data):
        return self._run(self.client.patch, user, *validators, **data)

    def _delete(self, user, *validators):
        return self._run(self.client.delete, user, *validators)

    def _run(self, method, user, *validators, **data):
        with register_validators(*validators):
            self.client.login(username=user.username, password=self.password)
            return method(
                reverse("dcim-api:manufacturer-detail", kwargs={"pk": self.manufacturer.pk}),
                content_type="application/json",
                data=data,
            )

    def test_protected_update(self):
        response = self._patch(
            self.user,
            ("dcim", "manufacturer"),
            description="new description",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["description"][0],
            f"The attribute is managed by the Design Instance: {self.deployment}. ",
        )

    def test_unprotected_delete(self):
        response = self._delete(
            self.user,
        )
        self.assertEqual(response.status_code, 204)

    def test_protected_delete(self):
        response = self._delete(
            self.user,
            ("dcim", "manufacturer"),
        )
        self.assertEqual(response.status_code, 409)

    def test_protected_update_as_admin(self):
        settings.PLUGINS_CONFIG["nautobot_design_builder"]["protected_superuser_bypass"] = True
        response = self._patch(
            self.admin,
            ("dcim", "manufacturer"),
            description="new description",
        )
        self.assertEqual(response.status_code, 200)


# class DataProtectionBaseTest(BaseDeploymentTest):  # pylint: disable=too-many-instance-attributes
#     """Data Protection Test."""

#     def setUp(self):
#         super().setUp()
#         self.original_name = "original equipment manufacturer"
#         self.manufacturer_from_design = Manufacturer.objects.create(name=self.original_name, description="something")
#         self.job_kwargs = {
#             "manufacturer": f"{self.manufacturer_from_design.pk}",
#             "instance": "my instance",
#         }

#         self.change_set = self.create_change_set(self.job, self.deployment, self.job_kwargs)
#         self.initial_record = ChangeRecord.objects.create(
#             design_object=self.manufacturer_from_design,
#             full_control=True,
#             changes={
#                 "name": {"old_value": None, "new_value": self.original_name},
#                 "description": {"old_value": None, "new_value": "something"},
#             },
#             change_set=self.change_set,
#             index=self.change_set._next_index(),  # pylint:disable=protected-access
#         )

#         self.client = Client()

#         self.user = User.objects.create_user(username="test_user", email="test@example.com", password="password123")
#         self.admin = User.objects.create_user(
#             username="test_user_admin", email="admin@example.com", password="password123", is_superuser=True
#         )

#         actions = ["view", "add", "change", "delete"]
#         permission, _ = ObjectPermission.objects.update_or_create(
#             name="dcim-manufacturer-test",
#             defaults={"constraints": {}, "actions": actions},
#         )
#         permission.validated_save()
#         permission.object_types.set([ContentType.objects.get(app_label="dcim", model="manufacturer")])
#         permission.users.set([self.user])


# class DataProtectionBaseTestWithDefaults(DataProtectionBaseTest):
#     """Test for Data Protection with defaults."""

#     @override_settings(PLUGINS_CONFIG=plugin_settings_with_defaults)
#     def test_update_as_user_without_protection(self):
#         register_custom_validators(custom_validators)
#         self.client.login(username="test_user", password="password123")
#         response = self.client.patch(
#             reverse("dcim-api:manufacturer-detail", kwargs={"pk": self.manufacturer_from_design.pk}),
#             data={"description": "new description"},
#             content_type="application/json",
#         )
#         self.assertEqual(response.status_code, 200)

#     @override_settings(PLUGINS_CONFIG=plugin_settings_with_defaults)
#     def test_delete_as_user_without_protection(self):
#         load_pre_delete_signals()
#         self.client.login(username="test_user", password="password123")
#         response = self.client.delete(
#             reverse("dcim-api:manufacturer-detail", kwargs={"pk": self.manufacturer_from_design.pk}),
#             content_type="application/json",
#         )
#         self.assertEqual(response.status_code, 204)


# class DataProtectionBaseTestWithProtection(DataProtectionBaseTest):
#     """Test for Data Protection with protected objects."""

#     @override_settings(PLUGINS_CONFIG=plugin_settings_with_protection)
#     def test_update_as_user_with_protection(self):
#         register_custom_validators(custom_validators)
#         self.client.login(username="test_user", password="password123")
#         response = self.client.patch(
#             reverse("dcim-api:manufacturer-detail", kwargs={"pk": self.manufacturer_from_design.pk}),
#             data={"description": "new description"},
#             content_type="application/json",
#         )

#         self.assertEqual(response.status_code, 400)
#         self.assertEqual(
#             response.json()["description"][0],
#             f"The attribute is managed by the Design Instance: {self.deployment}. ",
#         )

#     @override_settings(PLUGINS_CONFIG=plugin_settings_with_protection)
#     def test_update_as_admin_with_protection_and_with_bypass(self):
#         register_custom_validators(custom_validators)
#         self.client.login(username="test_user_admin", password="password123")
#         response = self.client.patch(
#             reverse("dcim-api:manufacturer-detail", kwargs={"pk": self.manufacturer_from_design.pk}),
#             data={"description": "new description"},
#             content_type="application/json",
#         )

#         self.assertEqual(response.status_code, 200)

#     @unittest.skip("Issue with TransactionManagerError in tests.")
#     @override_settings(PLUGINS_CONFIG=plugin_settings_with_protection)
#     def test_delete_as_user_with_protection(self):
#         load_pre_delete_signals()
#         self.client.login(username="test_user", password="password123")
#         response = self.client.delete(
#             reverse("dcim-api:manufacturer-detail", kwargs={"pk": self.manufacturer_from_design.pk}),
#             content_type="application/json",
#         )

#         self.assertEqual(response.status_code, 409)

#     @override_settings(PLUGINS_CONFIG=plugin_settings_with_protection)
#     def test_delete_as_admin_with_protection_and_with_bypass(self):
#         load_pre_delete_signals()
#         self.client.login(username="test_user_admin", password="password123")
#         response = self.client.delete(
#             reverse("dcim-api:manufacturer-detail", kwargs={"pk": self.manufacturer_from_design.pk}),
#             content_type="application/json",
#         )

#         self.assertEqual(response.status_code, 204)


# class DataProtectionBaseTestWithProtectionBypassDisabled(DataProtectionBaseTest):
#     """Test for Data Protection with data protection by superuser bypass."""

#     @override_settings(PLUGINS_CONFIG=plugin_settings_with_protection_and_superuser_bypass_disabled)
#     def test_update_as_admin_with_protection_and_without_bypass(self):
#         register_custom_validators(custom_validators)
#         self.client.login(username="test_user_admin", password="password123")
#         response = self.client.patch(
#             reverse("dcim-api:manufacturer-detail", kwargs={"pk": self.manufacturer_from_design.pk}),
#             data={"description": "new description"},
#             content_type="application/json",
#         )

#         self.assertEqual(response.status_code, 400)
#         self.assertEqual(
#             response.json()["description"][0],
#             f"The attribute is managed by the Design Instance: {self.deployment}. ",
#         )

#     @unittest.skip("Issue with TransactionManagerError in tests.")
#     @override_settings(PLUGINS_CONFIG=plugin_settings_with_protection_and_superuser_bypass_disabled)
#     def test_delete_as_admin_with_protection_and_without_bypass(self):
#         load_pre_delete_signals()
#         self.client.login(username="test_user_admin", password="password123")
#         response = self.client.delete(
#             reverse("dcim-api:manufacturer-detail", kwargs={"pk": self.manufacturer_from_design.pk}),
#             content_type="application/json",
#         )

#         self.assertEqual(response.status_code, 409)
