from rest_framework import viewsets, permissions, filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import EquipmentCategory, EquipmentPhysicalType, EquipmentModule, CompatibilityRule
from .serializers import EquipmentCategorySerializer, EquipmentPhysicalTypeSerializer, EquipmentModuleSerializer, CompatibilityRuleSerializer


class EquipmentCategoryViewSet(viewsets.ModelViewSet):
    """API для категорий оборудования (иерархия)"""
    queryset = EquipmentCategory.objects.all()
    serializer_class = EquipmentCategorySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter, DjangoFilterBackend]
    search_fields = ['name', 'description', 'code']
    ordering_fields = ['order', 'name']
    filterset_fields = ['parent', 'equipment_type', 'is_active']


class EquipmentPhysicalTypeViewSet(viewsets.ModelViewSet):
    """API для физических типов оборудования"""
    queryset = EquipmentPhysicalType.objects.all()
    serializer_class = EquipmentPhysicalTypeSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['order', 'name']


class EquipmentModuleViewSet(viewsets.ModelViewSet):
    """API для модулей оборудования"""
    queryset = EquipmentModule.objects.all()
    serializer_class = EquipmentModuleSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = [
        'category',
        'physical_type',
        'applicable_to',
        'is_active',
        'is_default',
        'price_type'
    ]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'price', 'created_at']


class CompatibilityRuleViewSet(viewsets.ModelViewSet):
    """API для правил совместимости"""
    queryset = CompatibilityRule.objects.all()
    serializer_class = CompatibilityRuleSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
