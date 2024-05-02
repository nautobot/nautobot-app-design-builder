"""UI URLs for design builder."""

from django.urls import path

from nautobot.apps.urls import NautobotUIViewSetRouter

from nautobot_design_builder.views import (
    DesignUIViewSet,
    DesignInstanceUIViewSet,
    JournalUIViewSet,
    JournalEntryUIViewSet,
    DesignProtectionObjectView,
)

router = NautobotUIViewSetRouter()
router.register("designs", DesignUIViewSet)
router.register("design-instances", DesignInstanceUIViewSet)
router.register("journals", JournalUIViewSet)
router.register("journal-entries", JournalEntryUIViewSet)

urlpatterns = router.urls

urlpatterns.append(
    path(
        "design-protection/<model>/<uuid:id>/",
        DesignProtectionObjectView.as_view(),
        name="design-protection-tab",
    ),
)
