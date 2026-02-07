from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from configurator.models import Configuration
from configurator.serializers import (
    ConfigurationSerializer,
    ConfigurationCreateSerializer,
    ConfigurationValidateSerializer
)
from catalog.models import EquipmentType, EquipmentModule


class ConfigurationViewSet(viewsets.ModelViewSet):
    """
    ViewSet для работы с конфигурациями.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Возвращаем только конфигурации текущего пользователя"""
        return Configuration.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        """Выбираем сериализатор в зависимости от действия"""
        if self.action in ['create', 'update', 'partial_update']:
            return ConfigurationCreateSerializer
        return ConfigurationSerializer

    def perform_create(self, serializer):
        """Создание конфигурации с текущим пользователем"""
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['get'])
    def validate(self, request, pk=None):
        """Валидация конкретной конфигурации"""
        configuration = self.get_object()

        # Вызываем метод валидации из модели
        is_valid, errors = configuration.validate_compatibility()

        serializer = ConfigurationValidateSerializer({
            'is_valid': is_valid,
            'errors': errors,
            'total_price': configuration.total_price
        })

        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def validate_new(self, request):
        """Валидация новой конфигурации без сохранения"""
        serializer = ConfigurationCreateSerializer(
            data=request.data,
            context={'request': request}
        )

        if serializer.is_valid():
            # Создаем временную конфигурацию для валидации
            config_data = serializer.validated_data
            config_data['user'] = request.user

            # Создаем объект без сохранения в БД
            temp_config = Configuration(**config_data)
            temp_config.id = None  # Гарантируем, что это новый объект

            # Валидируем
            is_valid, errors = temp_config.validate_compatibility()

            # Расчет цены
            temp_config.calculate_total_price()

            response_serializer = ConfigurationValidateSerializer({
                'is_valid': is_valid,
                'errors': errors,
                'total_price': temp_config.total_price
            })

            return Response(response_serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def equipment_types(self, request):
        """Получение списка типов оборудования"""
        equipment_types = EquipmentType.objects.all()
        data = [{'id': et.id, 'name': et.name} for et in equipment_types]
        return Response(data)

    @action(detail=False, methods=['get'])
    def available_modules(self, request):
        """Получение модулей для выбранного типа оборудования"""
        equipment_type_id = request.query_params.get('equipment_type_id')

        if not equipment_type_id:
            return Response(
                {'error': 'equipment_type_id параметр обязателен'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            equipment_type = EquipmentType.objects.get(id=equipment_type_id)
            modules = EquipmentModule.objects.filter(
                compatible_types=equipment_type
            )
            data = [{'id': m.id, 'name': m.name, 'price': str(m.price)} for m in modules]
            return Response(data)
        except EquipmentType.DoesNotExist:
            return Response(
                {'error': 'Тип оборудования не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
