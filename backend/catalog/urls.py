from django.urls import include, path
from rest_framework import routers

from .api import (
    CompatibilityRuleViewSet,
    EngineeringSystemGroupViewSet,
    EngineeringSystemOptionViewSet,
    EquipmentCategoryViewSet,
    EquipmentModuleViewSet,
    EquipmentPhysicalTypeViewSet,
)
from .api_views import EngineeringSystemsView, EquipmentTypesView

router = routers.DefaultRouter()
router.register(r"equipment-categories", EquipmentCategoryViewSet)
router.register(r"equipment-physical-types", EquipmentPhysicalTypeViewSet)
router.register(r"equipment-modules", EquipmentModuleViewSet)
router.register(r"compatibility-rules", CompatibilityRuleViewSet)


# Раздел 2 ТЗ: инженерные системы (группы + опции по группе)
router.register(r"engineering-system-groups", EngineeringSystemGroupViewSet)
router.register(
    r"engineering-system-options",
    EngineeringSystemOptionViewSet,
    basename="engineering-system-options",
)


urlpatterns = [
    path("", include(router.urls)),
    path("equipment-types/", EquipmentTypesView.as_view(), name="equipment-types"),
    path(
        "engineering_systems/",
        EngineeringSystemsView.as_view(),
        name="engineering_systems",
    ),
    path(
        "engineering-systems/",
        EngineeringSystemsView.as_view(),
        name="engineering-systems",
    ),
    path("engineering/", EngineeringSystemsView.as_view(), name="engineering"),
    path(
        "engineeringsystems/",
        EngineeringSystemsView.as_view(),
        name="engineeringsystems",
    ),
]
