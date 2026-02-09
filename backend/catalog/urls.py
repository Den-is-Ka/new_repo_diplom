from django.urls import path, include
from rest_framework import routers
from .api import (
    EquipmentCategoryViewSet,
    EquipmentPhysicalTypeViewSet,
    EquipmentModuleViewSet,
    CompatibilityRuleViewSet
)

router = routers.DefaultRouter()
router.register(r'equipment-categories', EquipmentCategoryViewSet)
router.register(r'equipment-physical-types', EquipmentPhysicalTypeViewSet)
router.register(r'equipment-modules', EquipmentModuleViewSet)
router.register(r'compatibility-rules', CompatibilityRuleViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
