"""API URLs for design builder."""

from nautobot.core.api import OrderedDefaultRouter
from nautobot_design_builder.api.views import (
    DesignAPIViewSet,
    DeploymentAPIViewSet,
    JournalAPIViewSet,
    JournalEntryAPIViewSet,
)

router = OrderedDefaultRouter()

router.register("designs", DesignAPIViewSet)
router.register("design-instances", DeploymentAPIViewSet)
router.register("journals", JournalAPIViewSet)
router.register("journal-entries", JournalEntryAPIViewSet)

urlpatterns = router.urls
