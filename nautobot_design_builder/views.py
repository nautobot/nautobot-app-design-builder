"""Views for nautobot_design_builder."""

from nautobot.apps.views import NautobotUIViewSet
from nautobot.apps.ui import ObjectDetailContent, ObjectFieldsPanel, ObjectTablePanel, SectionChoices
from nautobot.core.templatetags import helpers

from nautobot_design_builder import filters, forms, models, tables
from nautobot_design_builder.api import serializers


class DesignUIViewSet(NautobotUIViewSet):
    """ViewSet for Design views."""

    bulk_update_form_class = forms.DesignBulkEditForm
    filterset_class = filters.DesignFilterSet
    filterset_form_class = forms.DesignFilterForm
    form_class = forms.DesignForm
    lookup_field = "pk"
    queryset = models.Design.objects.all()
    serializer_class = serializers.DesignSerializer
    table_class = tables.DesignTable

    # Here is an example of using the UI  Component Framework for the detail view.
    # More information can be found in the Nautobot documentation:
    # https://docs.nautobot.com/projects/core/en/stable/development/core/ui-component-framework/
    object_detail_content = ObjectDetailContent(
        panels=[
            ObjectFieldsPanel(
                weight=100,
                section=SectionChoices.LEFT_HALF,
                fields="__all__",
                # Alternatively, you can specify a list of field names:
                # fields=[
                #     "name",
                #     "description",
                # ],
                # Some fields may require additional configuration, we can use value_transforms
                # value_transforms={
                #     "name": [helpers.bettertitle]
                # },
            ),
            # If there is a ForeignKey or M2M with this model we can use ObjectTablePanel
            # to display them in a table format.
            # ObjectTablePanel(
                # weight=200,
                # section=SectionChoices.RIGHT_HALF,
                # table_class=tables.DesignTable,
                # You will want to filter the table using the related_name
                # filter="designs",
            # ),
        ],
    )
