from django.urls import path, include
from rest_framework import routers

from .api import (
    EquipmentCategoryViewSet,
    EquipmentPhysicalTypeViewSet,
    EquipmentModuleViewSet,
    CompatibilityRuleViewSet,
    EngineeringSystemGroupViewSet,
    EngineeringSystemOptionViewSet,
)

router = routers.DefaultRouter()
router.register(r'equipment-categories', EquipmentCategoryViewSet)
router.register(r'equipment-physical-types', EquipmentPhysicalTypeViewSet)
router.register(r'equipment-modules', EquipmentModuleViewSet)
router.register(r'compatibility-rules', CompatibilityRuleViewSet)


# Раздел 2 ТЗ: инженерные системы (группы + опции по группе)
router.register(r'engineering-system-groups', EngineeringSystemGroupViewSet)
router.register(r'engineering-system-options', EngineeringSystemOptionViewSet, basename='engineering-system-options')


urlpatterns = [
    path('', include(router.urls)),
]
