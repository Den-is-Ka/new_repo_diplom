from rest_framework import viewsets, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response

from django_filters.rest_framework import DjangoFilterBackend

from .models import (
    EquipmentCategory,
    EquipmentPhysicalType,
    EquipmentModule,
    CompatibilityRule,
    EngineeringSystemGroup,
    EngineeringSystemOption,
)

from .serializers import (
    EquipmentCategorySerializer,
    EquipmentPhysicalTypeSerializer,
    EquipmentModuleSerializer,
    CompatibilityRuleSerializer,
    EngineeringSystemGroupSerializer,
    EngineeringSystemOptionSerializer,
)


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


# =========================
# Раздел 2 ТЗ: Инженерные системы (группы + опции)
# =========================

class EngineeringSystemGroupViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Список групп (2.1–2.9)
    GET /catalog/engineering-system-groups/?is_active=true&ordering=order
    """
    queryset = EngineeringSystemGroup.objects.all()
    serializer_class = EngineeringSystemGroupSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ['is_active']
    ordering_fields = ['order', 'code', 'title']
    search_fields = ['title', 'code']

    def get_queryset(self):
        qs = super().get_queryset()
        if 'ordering' not in self.request.query_params:
            qs = qs.order_by('order', 'code')
        return qs

    # Опционально: оставляем nested endpoint (удобно)
    @action(detail=True, methods=['get'], url_path='options')
    def options(self, request, pk=None):
        """
        Опции по группе (nested)
        GET /catalog/engineering-system-groups/<id>/options/?is_active=true&ordering=order
        """
        group = self.get_object()

        qs = EngineeringSystemOption.objects.filter(group=group)

        # DRF ordering
        ordering = request.query_params.get('ordering')
        if ordering:
            qs = qs.order_by(*[p.strip() for p in ordering.split(',') if p.strip()])
        else:
            qs = qs.order_by('order', 'code')

        # Фильтр is_active (как boolean через строку)
        is_active = request.query_params.get('is_active')
        if is_active is not None:
            val = str(is_active).lower()
            if val in ('1', 'true', 'yes', 'y', 'on'):
                qs = qs.filter(is_active=True)
            elif val in ('0', 'false', 'no', 'n', 'off'):
                qs = qs.filter(is_active=False)

        serializer = EngineeringSystemOptionSerializer(qs, many=True, context={'request': request})
        return Response(serializer.data)


class EngineeringSystemOptionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Опции инженерных систем (2.1.1, 2.1.2 ...)
    GET /catalog/engineering-system-options/?group=<group_id>&is_active=true&ordering=order
    """
    queryset = EngineeringSystemOption.objects.select_related('group').all()
    serializer_class = EngineeringSystemOptionSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ['group', 'is_active', 'price_type', 'applicability']
    ordering_fields = ['order', 'code', 'title', 'price']
    search_fields = ['title', 'code', 'group__title', 'group__code']

    def get_queryset(self):
        qs = super().get_queryset()
        if 'ordering' not in self.request.query_params:
            qs = qs.order_by('group__order', 'order', 'code')
        return qs
