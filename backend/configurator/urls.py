from django.urls import include, path
from rest_framework.routers import DefaultRouter

from configurator import views

router = DefaultRouter()
router.register(r"configurations", views.ConfigurationViewSet, basename="configuration")

urlpatterns = [
    path("", include(router.urls)),
]
