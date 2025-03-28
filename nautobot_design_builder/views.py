"""Views for nautobot_design_builder."""

from nautobot.apps.views import NautobotUIViewSet

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
