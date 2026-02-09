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
from catalog.models import EquipmentCategory, EquipmentModule


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

        # TODO: Реализовать метод валидации в модели
        is_valid = True
        errors = []

        # Временная заглушка для валидации
        if not configuration.modules.exists():
            is_valid = False
            errors.append("Конфигурация должна содержать хотя бы один модуль")

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

            # Валидируем (временная заглушка)
            is_valid = True
            errors = []

            # Проверка минимальных требований
            if not config_data.get('modules'):
                is_valid = False
                errors.append("Конфигурация должна содержать хотя бы один модуль")

            # Расчет цены
            total_price = temp_config.calculate_total_price()

            response_serializer = ConfigurationValidateSerializer({
                'is_valid': is_valid,
                'errors': errors,
                'total_price': total_price
            })

            return Response(response_serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def main_categories(self, request):
        """Получение списка основных категорий (1.1 и 1.2)"""
        main_categories = EquipmentCategory.objects.filter(
            parent__isnull=False,
            parent__parent__isnull=True
        ).select_related('parent')

        data = []
        for category in main_categories:
            data.append({
                'id': category.id,
                'name': category.name,
                'parent_name': category.parent.name if category.parent else '',
                'equipment_type': category.equipment_type,
                'description': category.description
            })
        return Response(data)

    @action(detail=False, methods=['get'])
    def sub_categories(self, request):
        """Получение подкатегорий для выбранной основной категории"""
        main_category_id = request.query_params.get('main_category_id')

        if not main_category_id:
            return Response(
                {'error': 'main_category_id параметр обязателен'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            main_category = EquipmentCategory.objects.get(id=main_category_id)
            sub_categories = EquipmentCategory.objects.filter(
                parent=main_category
            )
            data = []
            for sub in sub_categories:
                data.append({
                    'id': sub.id,
                    'name': sub.name,
                    'code': sub.code,
                    'description': sub.description,
                    'is_active': sub.is_active
                })
            return Response(data)
        except EquipmentCategory.DoesNotExist:
            return Response(
                {'error': 'Основная категория не найдена'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['get'])
    def available_modules(self, request):
        """Получение модулей для выбранной категории"""
        category_id = request.query_params.get('category_id')
        applicable_to = request.query_params.get('applicable_to')  # DGU или COMPRESSOR

        if not category_id:
            return Response(
                {'error': 'category_id параметр обязателен'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            category = EquipmentCategory.objects.get(id=category_id)

            # Получаем модули для этой категории
            modules = EquipmentModule.objects.filter(
                category=category,
                is_active=True
            )

            # Фильтрация по применимости, если указана
            if applicable_to:
                modules = modules.filter(applicable_to__in=[applicable_to, 'BOTH'])

            data = []
            for module in modules:
                data.append({
                    'id': module.id,
                    'name': module.name,
                    'description': module.description,
                    'price': str(module.price) if module.price else None,
                    'price_type': module.price_type,
                    'display_price': module.display_price,
                    'physical_type': module.physical_type.name if module.physical_type else '',
                    'applicable_to': module.applicable_to
                })
            return Response(data)
        except EquipmentCategory.DoesNotExist:
            return Response(
                {'error': 'Категория не найдена'},
                status=status.HTTP_404_NOT_FOUND
            )
