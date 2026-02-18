from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from configurator.models import Configuration
from configurator.serializers import (
    ConfigurationSerializer,
    ConfigurationCreateSerializer,
    ConfigurationValidateSerializer,
)
from catalog.models import EquipmentCategory, EquipmentModule

from orders.services import submit_configuration


class ConfigurationViewSet(viewsets.ModelViewSet):
    """
    ViewSet для работы с конфигурациями.
    """
    queryset = Configuration.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Возвращаем только конфигурации текущего пользователя"""
        return Configuration.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        """Выбираем сериализатор в зависимости от действия"""
        if self.action in ["create", "update", "partial_update"]:
            return ConfigurationCreateSerializer
        return ConfigurationSerializer

    def perform_create(self, serializer):
        """Создание конфигурации с текущим пользователем"""
        serializer.save(user=self.request.user)

    @action(detail=True, methods=["get"])
    def validate(self, request, pk=None):
        """Валидация конкретной конфигурации (пока простая заглушка)"""
        configuration = self.get_object()

        is_valid = True
        errors = []

        # Временная заглушка (позже заменишь на rule-engine)
        if not configuration.modules.exists():
            is_valid = False
            errors.append("Конфигурация должна содержать хотя бы один модуль")

        serializer = ConfigurationValidateSerializer(
            {
                "is_valid": is_valid,
                "errors": errors,
                "total_price": configuration.total_price,
            }
        )
        return Response(serializer.data)

    @action(detail=False, methods=["post"])
    def validate_new(self, request):
        """Валидация новой конфигурации без сохранения"""
        serializer = ConfigurationCreateSerializer(
            data=request.data, context={"request": request}
        )

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        config_data = serializer.validated_data
        config_data["user"] = request.user

        # Создаем объект без сохранения в БД
        temp_config = Configuration(**config_data)
        temp_config.id = None

        is_valid = True
        errors = []

        if not config_data.get("modules"):
            is_valid = False
            errors.append("Конфигурация должна содержать хотя бы один модуль")

        total_price = temp_config.calculate_total_price()

        response_serializer = ConfigurationValidateSerializer(
            {
                "is_valid": is_valid,
                "errors": errors,
                "total_price": total_price,
            }
        )
        return Response(response_serializer.data)

    @action(detail=False, methods=["get"])
    def main_categories(self, request):
        """Получение списка основных категорий (1.1 и 1.2)"""
        main_categories = (
            EquipmentCategory.objects.filter(
                parent__isnull=False,
                parent__parent__isnull=True,
            )
            .select_related("parent")
            .order_by("id")
        )

        data = []
        for category in main_categories:
            data.append(
                {
                    "id": category.id,
                    "name": category.name,
                    "parent_name": category.parent.name if category.parent else "",
                    "equipment_type": category.equipment_type,
                    "description": getattr(category, "description", "") or "",
                }
            )
        return Response(data)

    @action(detail=False, methods=["get"])
    def sub_categories(self, request):
        """Получение подкатегорий для выбранной основной категории"""
        main_category_id = request.query_params.get("main_category_id")

        if not main_category_id:
            return Response(
                {"error": "main_category_id параметр обязателен"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            main_category = EquipmentCategory.objects.get(id=main_category_id)
        except EquipmentCategory.DoesNotExist:
            return Response(
                {"error": "Основная категория не найдена"},
                status=status.HTTP_404_NOT_FOUND,
            )

        subs = EquipmentCategory.objects.filter(parent=main_category).order_by("id")

        data = []
        for sub in subs:
            data.append(
                {
                    "id": sub.id,
                    "name": sub.name,
                    "code": getattr(sub, "code", ""),
                    "description": getattr(sub, "description", "") or "",
                    "is_active": getattr(sub, "is_active", True),
                }
            )
        return Response(data)

    @action(detail=False, methods=["get"])
    def available_modules(self, request):
        """Получение модулей для выбранной категории"""
        category_id = request.query_params.get("category_id")
        applicable_to = request.query_params.get("applicable_to")

        if not category_id:
            return Response(
                {"error": "category_id параметр обязателен"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            category = EquipmentCategory.objects.get(id=category_id)
        except EquipmentCategory.DoesNotExist:
            return Response(
                {"error": "Категория не найдена"},
                status=status.HTTP_404_NOT_FOUND,
            )

        modules = EquipmentModule.objects.filter(category=category, is_active=True)

        if applicable_to:
            modules = modules.filter(applicable_to__in=[applicable_to, "BOTH"])

        data = []
        for module in modules:
            data.append(
                {
                    "id": module.id,
                    "name": module.name,
                    "description": getattr(module, "description", "") or "",
                    "price": str(module.price) if module.price else None,
                    "price_type": module.price_type,
                    "display_price": getattr(module, "display_price", ""),
                    "physical_type": module.physical_type.name if module.physical_type else "",
                    "applicable_to": getattr(module, "applicable_to", ""),
                }
            )
        return Response(data)

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        """
        Отправка конфигурации производителю:
        - идемпотентно создает Order (1 конфигурация -> 1 заказ) через OneToOne
        - фиксирует snapshot и total_price
        - защищено от гонок (atomic + select_for_update) внутри сервиса
        """
        configuration = self.get_object()

        # ✅ OneToOne: если заказ уже есть — возвращаем его
        existing_order = getattr(configuration, "order", None)
        if existing_order is not None:
            return Response(
                {
                    "order_id": existing_order.id,
                    "order_number": existing_order.order_number,
                    "status": existing_order.status,
                    "total_price": str(existing_order.total_price),
                    "created": False,
                },
                status=status.HTTP_200_OK,
            )

        try:
            order, created = submit_configuration(
                configuration_id=configuration.id,
                user=request.user,
            )
            return Response(
                {
                    "order_id": order.id,
                    "order_number": order.order_number,
                    "status": order.status,
                    "total_price": str(order.total_price),
                    "created": created,
                },
                status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
            )
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
