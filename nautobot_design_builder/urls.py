"""UI URLs for design builder."""
from nautobot.core.views.routers import NautobotUIViewSetRouter
from django.urls import path

from nautobot_design_builder.views import (
    DesignUIViewSet,
    DesignInstanceUIViewSet,
    JournalUIViewSet,
    JournalEntryUIViewSet,
    # DecommissionJobView,
)

router = NautobotUIViewSetRouter()
router.register("designs", DesignUIViewSet)
router.register("design-instances", DesignInstanceUIViewSet)
router.register("journals", JournalUIViewSet)
router.register("journal-entries", JournalEntryUIViewSet)

# urlpatterns = []

# urlpatterns.append(
#     path("design-instances/<uuid:pk>/decommission/", DecommissionJobView.as_view(), name="decommissioning_job"),
# )
# urlpatterns.append(
#     path("design-instances/decommission/", DecommissionJobView.as_view(), name="decommissioning_job"),
# )
urlpatterns = router.urls
