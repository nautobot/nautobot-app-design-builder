"""UI URLs for design builder."""
from nautobot.core.views.routers import NautobotUIViewSetRouter

from design_builder.views import DesignUIViewSet, DesignInstanceUIViewSet, JournalUIViewSet, JournalEntryUIViewSet

router = NautobotUIViewSetRouter()
router.register("designs", DesignUIViewSet)
router.register("design-instances", DesignInstanceUIViewSet)
router.register("journals", JournalUIViewSet)
router.register("journal-entries", JournalEntryUIViewSet)

urlpatterns = router.urls
