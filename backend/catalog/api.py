from rest_framework import viewsets, permissions, filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import EquipmentType, EquipmentModule, CompatibilityRule
from .serializers import EquipmentTypeSerializer, EquipmentModuleSerializer, CompatibilityRuleSerializer

class EquipmentTypeViewSet(viewsets.ModelViewSet):
    queryset = EquipmentType.objects.all()
    serializer_class = EquipmentTypeSerializer  # ДОБАВИТЬ ЭТУ СТРОКУ
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'order']

class EquipmentModuleViewSet(viewsets.ModelViewSet):
    queryset = EquipmentModule.objects.all()
    serializer_class = EquipmentModuleSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['equipment_type', 'is_active', 'is_default', 'price_type']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'price', 'created_at']

class CompatibilityRuleViewSet(viewsets.ModelViewSet):
    queryset = CompatibilityRule.objects.all()
    serializer_class = CompatibilityRuleSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
