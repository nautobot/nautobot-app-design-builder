"""API URLs for design builder."""

from nautobot.apps.api import OrderedDefaultRouter

from nautobot_design_builder.api.views import (
    ChangeRecordAPIViewSet,
    ChangeSetAPIViewSet,
    DeploymentAPIViewSet,
    DesignAPIViewSet,
)

router = OrderedDefaultRouter()

router.register("designs", DesignAPIViewSet)
router.register("deployments", DeploymentAPIViewSet)
router.register("change-sets", ChangeSetAPIViewSet)
router.register("change-records", ChangeRecordAPIViewSet)

app_name = "nautobot_design_builder-api"
urlpatterns = router.urls
