from django.urls import path, include
from rest_framework import routers
from .api import EquipmentTypeViewSet, EquipmentModuleViewSet, CompatibilityRuleViewSet

router = routers.DefaultRouter()
router.register(r'equipment-types', EquipmentTypeViewSet)
router.register(r'equipment-modules', EquipmentModuleViewSet)
router.register(r'compatibility-rules', CompatibilityRuleViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
