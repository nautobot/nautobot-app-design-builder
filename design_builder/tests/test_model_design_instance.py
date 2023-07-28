"""Test DesignInstance."""

from django.core.exceptions import ValidationError
from django.db import IntegrityError

from .test_model_design import BaseDesignTest
from .. import models


class BaseDesignInstanceTest(BaseDesignTest):
    """Base fixtures for tests using design instances."""
    def setUp(self):
        super().setUp()
        self.design_name = "My Design"
        self.design_instance = models.DesignInstance(design=self.design1, name=self.design_name)
        self.design_instance.validated_save()


class TestDesignInstance(BaseDesignInstanceTest):
    """Test DesignInstance."""
    def test_design_instance_queryset(self):
        design = models.DesignInstance.objects.get_by_natural_key(self.job1.name, self.design_name)
        self.assertIsNotNone(design)
        self.assertEqual("Simple Design - My Design", str(design))

    def test_design_cannot_be_changed(self):
        with self.assertRaises(ValidationError):
            self.design_instance.design = self.design2
            self.design_instance.validated_save()

        with self.assertRaises(ValidationError):
            self.design_instance.design = None
            self.design_instance.validated_save()

    def test_uniqueness(self):
        with self.assertRaises(IntegrityError):
            models.DesignInstance.objects.create(design=self.design1, name=self.design_name)
