"""Forms for nautobot_design_builder."""

from django import forms
from nautobot.apps.constants import CHARFIELD_MAX_LENGTH
from nautobot.apps.forms import NautobotBulkEditForm, NautobotFilterForm, NautobotModelForm, TagsBulkEditFormMixin

from nautobot_design_builder import models


class DesignForm(NautobotModelForm):  # pylint: disable=too-many-ancestors
    """Design creation/edit form."""

    class Meta:
        """Meta attributes."""

        model = models.Design
        fields = "__all__"


class DesignBulkEditForm(TagsBulkEditFormMixin, NautobotBulkEditForm):  # pylint: disable=too-many-ancestors
    """Design bulk edit form."""

    pk = forms.ModelMultipleChoiceField(queryset=models.Design.objects.all(), widget=forms.MultipleHiddenInput)
    description = forms.CharField(required=False, max_length=CHARFIELD_MAX_LENGTH)

    class Meta:
        """Meta attributes."""

        nullable_fields = [
            "description",
        ]


class DesignFilterForm(NautobotFilterForm):  # pylint: disable=too-many-ancestors
    """Filter form to filter searches."""

    model = models.Design
    field_order = ["q", "name"]

    q = forms.CharField(
        required=False,
        label="Search",
        help_text="Search within Name.",
    )
    name = forms.CharField(required=False, label="Name")
