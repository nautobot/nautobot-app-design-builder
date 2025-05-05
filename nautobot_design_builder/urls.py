"""UI URLs for design builder."""

from django.templatetags.static import static
from django.urls import path
from django.views.generic import RedirectView
from nautobot.apps.urls import NautobotUIViewSetRouter

from nautobot_design_builder.views import (
    ChangeRecordUIViewSet,
    ChangeSetUIViewSet,
    DeploymentUIViewSet,
    DesignProtectionObjectView,
    DesignUIViewSet,
)

app_name = "nautobot_design_builder"
router = NautobotUIViewSetRouter()
router.register("designs", DesignUIViewSet)
router.register("deployments", DeploymentUIViewSet)
router.register("change-sets", ChangeSetUIViewSet)
router.register("change-records", ChangeRecordUIViewSet)


urlpatterns = [
    path("docs/", RedirectView.as_view(url=static("nautobot_design_builder/docs/index.html")), name="docs"),
    path(
        "design-protection/<model>/<uuid:id>/",
        DesignProtectionObjectView.as_view(),
        name="design-protection-tab",
    ),
]

urlpatterns += router.urls
