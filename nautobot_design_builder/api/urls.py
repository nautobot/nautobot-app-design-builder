"""API URLs for design builder."""

from nautobot.core.api import OrderedDefaultRouter
from nautobot_design_builder.api.views import (
    DesignAPIViewSet,
    DeploymentAPIViewSet,
    ChangeSetAPIViewSet,
    ChangeRecordAPIViewSet,
)

router = OrderedDefaultRouter()

router.register("designs", DesignAPIViewSet)
router.register("design-deployments", DeploymentAPIViewSet)
router.register("change-sets", ChangeSetAPIViewSet)
router.register("change-records", ChangeRecordAPIViewSet)

urlpatterns = router.urls
