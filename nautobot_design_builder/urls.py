"""UI URLs for design builder."""

from django.urls import path

from nautobot.core.views.routers import NautobotUIViewSetRouter

from nautobot_design_builder.views import (
    DesignUIViewSet,
    DeploymentUIViewSet,
    ChangeSetUIViewSet,
    ChangeRecordUIViewSet,
    DesignProtectionObjectView,
)

router = NautobotUIViewSetRouter()
router.register("designs", DesignUIViewSet)
router.register("design-deployments", DeploymentUIViewSet)
router.register("change-sets", ChangeSetUIViewSet)
router.register("change-records", ChangeRecordUIViewSet)

urlpatterns = router.urls

urlpatterns.append(
    path(
        "design-protection/<model>/<uuid:id>/",
        DesignProtectionObjectView.as_view(),
        name="design-protection-tab",
    ),
)
