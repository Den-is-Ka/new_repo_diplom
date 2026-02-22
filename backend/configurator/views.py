from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError

from users.roles import is_admin, is_manufacturer  # ✅ добавили роли

from configurator.models import Configuration, ConfigurationEngineeringSystem
from configurator.serializers import (
    ConfigurationSerializer,
    ConfigurationCreateSerializer,
    ConfigurationValidateSerializer,
    ConfigurationSetEngineeringSerializer,
)
from configurator.services import validate_configuration_for_submit
from catalog.models import EquipmentCategory, EquipmentModule, EngineeringSystemOption

from orders.services import submit_configuration


class ConfigurationViewSet(viewsets.ModelViewSet):
    """
    ViewSet для работы с конфигурациями.

    День 1 (P0): Права и фильтрация
    - admin: видит все конфигурации
    - manufacturer: конфигурации не видит
    - client: видит только свои
    """
    queryset = Configuration.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Возвращаем только конфигурации текущего пользователя (надёжно по user_id)."""
        user_id = getattr(getattr(self.request, "user", None), "id", None)
        if not user_id:
            return Configuration.objects.none()
        return Configuration.objects.filter(user_id=user_id)

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
        """
        Реальная валидация сохранённой конфигурации:
        - те же правила, что и у submit
        - возвращает is_valid/errors/total_price
        """
        configuration = self.get_object()

        is_valid = True
        errors = []

        try:
            validate_configuration_for_submit(configuration)
        except ValidationError as e:
            is_valid = False
            payload = e.detail
            details = payload.get("details", [])
            errors = [str(d.get("message")) for d in details]

        serializer = ConfigurationValidateSerializer(
            {
                "is_valid": is_valid,
                "errors": errors,
                "total_price": configuration.calculate_total_price(),
            }
        )
        return Response(serializer.data)

    @action(detail=False, methods=["post"])
    def validate_new(self, request):
        """
        Реальная валидация новой конфигурации без сохранения.
        """
        serializer = ConfigurationCreateSerializer(
            data=request.data, context={"request": request}
        )

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        config_data = serializer.validated_data
        config_data["user"] = request.user

        temp_config = Configuration(**config_data)
        temp_config.id = None

        is_valid = True
        errors = []

        try:
            validate_configuration_for_submit(temp_config)
        except ValidationError as e:
            is_valid = False
            payload = e.detail
            details = payload.get("details", [])
            errors = [str(d.get("message")) for d in details]

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
    def set_engineering(self, request, pk=None):
        """
        Установить (replace) инженерные системы для конфигурации.
        Body: {"engineering_option_ids":[31,34,39]}
        """
        configuration = self.get_object()

        # Жёстко: только для черновика (по ТЗ/lifecycle)
        if configuration.status != Configuration.Status.DRAFT:
            return Response(
                {"detail": "Engineering systems can be changed only in DRAFT status."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ser = ConfigurationSetEngineeringSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ids = ser.validated_data["engineering_option_ids"]

        # replace: удаляем старые
        ConfigurationEngineeringSystem.objects.filter(configuration=configuration).delete()

        # добавляем новые
        opts = EngineeringSystemOption.objects.filter(id__in=ids, is_active=True).select_related("group")
        by_id = {o.id: o for o in opts}

        for oid in ids:
            opt = by_id.get(oid)
            if not opt:
                continue
            ConfigurationEngineeringSystem.objects.create(
                configuration=configuration,
                engineering_system=opt,
                quantity=1,
                price_at_selection=opt.price if opt.price_type == "fixed" else None,
            )

        # обновим цену
        configuration.total_price = configuration.calculate_total_price()
        configuration.save(update_fields=["total_price", "updated_at"])

        return Response(
            {
                "configuration_id": configuration.id,
                "engineering_option_ids": ids,
                "total_price": str(configuration.total_price),
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        """
        Отправка конфигурации производителю:
        - идемпотентно создает Order (1 конфигурация -> 1 заказ) через OneToOne
        - фиксирует snapshot и total_price
        - защищено от гонок (atomic + select_for_update) внутри сервиса
        """
        configuration = self.get_object()

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

        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
