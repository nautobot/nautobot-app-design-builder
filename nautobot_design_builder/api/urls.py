"""Django API urlpatterns declaration for nautobot_design_builder app."""

from nautobot.apps.api import OrderedDefaultRouter

from nautobot_design_builder.api import views

router = OrderedDefaultRouter()
# add the name of your api endpoint, usually hyphenated model name in plural, e.g. "my-model-classes"
router.register("design", views.DesignViewSet)

app_name = "nautobot_design_builder-api"
urlpatterns = router.urls
