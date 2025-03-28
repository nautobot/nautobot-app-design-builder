"""Django urlpatterns declaration for nautobot_design_builder app."""

from django.templatetags.static import static
from django.urls import path
from django.views.generic import RedirectView
from nautobot.apps.urls import NautobotUIViewSetRouter


from nautobot_design_builder import views


app_name = "nautobot_design_builder"
router = NautobotUIViewSetRouter()

router.register("design", views.DesignUIViewSet)


urlpatterns = [
    path("docs/", RedirectView.as_view(url=static("nautobot_design_builder/docs/index.html")), name="docs"),
]

urlpatterns += router.urls
