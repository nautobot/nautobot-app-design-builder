"""Test Data Protection features."""

from contextlib import contextmanager
from copy import deepcopy

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import Client
from django.urls import reverse
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
    pre_validators = deepcopy(validators_registry)
    validators = []
    for app_label, model in models:
        validators.append(BaseValidator.factory(app_label, model))
    register_custom_validators(validators)
    yield
    for validator in validators:
        validator.disconnect()
    for key in list(validators_registry):
        validators_registry.pop(key)
    validators_registry.update(pre_validators)


class CustomValidatorTest(BaseDeploymentTest):
    """Test the Design Builder custom validator."""

    def setUp(self):
        super().setUp()
        self.change_set = self.create_change_set(self.jobs[0], self.deployment, {})
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

        self.password = User.objects.make_random_password()
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
        middleware = filter(lambda item: not item.endswith("ObjectChangeMiddleware"), settings.MIDDLEWARE)
        with self.settings(MIDDLEWARE=list(middleware)):
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
