"""API URLs for design builder."""
from nautobot.core.api import OrderedDefaultRouter
from nautobot_design_builder.api.views import (
    DesignAPIViewSet,
    DesignInstanceAPIViewSet,
    JournalAPIViewSet,
    JournalEntryAPIViewSet,
)

router = OrderedDefaultRouter()

router.register("designs", DesignAPIViewSet)
router.register("design-instances", DesignInstanceAPIViewSet)
router.register("journals", JournalAPIViewSet)
router.register("journal-entries", JournalEntryAPIViewSet)

urlpatterns = router.urls
