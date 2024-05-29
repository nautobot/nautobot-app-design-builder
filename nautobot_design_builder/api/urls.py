"""API URLs for design builder."""

from nautobot.apps.api import OrderedDefaultRouter
from nautobot_design_builder.api.views import (
    DesignAPIViewSet,
    DeploymentAPIViewSet,
    JournalAPIViewSet,
    JournalEntryAPIViewSet,
)

router = OrderedDefaultRouter()

router.register("designs", DesignAPIViewSet)
router.register("deployments", DeploymentAPIViewSet)
router.register("journals", JournalAPIViewSet)
router.register("journal-entries", JournalEntryAPIViewSet)

urlpatterns = router.urls
