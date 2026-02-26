from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from catalog.models import EngineeringSystemOption, EquipmentCategory, EquipmentModule
from configurator.models import Configuration, ConfigurationEngineeringSystem
from configurator.serializers import (
    ConfigurationCreateSerializer,
    ConfigurationSerializer,
    ConfigurationSetEngineeringSerializer,
    ConfigurationValidateSerializer,
)
from configurator.services import validate_configuration_for_submit
from orders.services import submit_configuration
from users.roles import is_manufacturer


def _role_str(user) -> str:
    role = getattr(user, "role", None) or getattr(user, "user_type", None)
    return str(role).lower() if role is not None else ""


class ConfigurationViewSet(viewsets.ModelViewSet):
    queryset = Configuration.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = (
            Configuration.objects.all()
            .select_related("user", "main_category", "sub_category")
            .prefetch_related("modules")
        )

        user = getattr(self.request, "user", None)
        if not user or not user.is_authenticated:
            return qs.none()

        if user.is_staff or user.is_superuser:
            return qs

        r = _role_str(user)
        if r in ("admin", "staff"):
            return qs

        if is_manufacturer(user) or r == "manufacturer":
            return qs.none()

        return qs.filter(user=user)

    def get_serializer_class(self):
        # Create serializer — только для входных данных (create/update/patch)
        if self.action in ["create", "update", "partial_update"]:
            return ConfigurationCreateSerializer
        return ConfigurationSerializer

    # ---------- helpers ----------
    def _lock_if_not_draft(self, instance: Configuration) -> Response | None:
        if instance.status != Configuration.Status.DRAFT:
            return Response(
                {"detail": "Configuration is locked after submit."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return None

    def _recalc_total_price_safe(self, cfg: Configuration) -> None:
        try:
            cfg.total_price = cfg.calculate_total_price()
            cfg.save(update_fields=["total_price", "updated_at"])
        except Exception:
            pass

    def _response_full_cfg(
        self, cfg: Configuration, http_status=status.HTTP_200_OK
    ) -> Response:
        data = ConfigurationSerializer(cfg, context={"request": self.request}).data
        return Response(data, status=http_status)

    # ---------- create / update / patch ----------
    def create(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data, context={"request": request})
        ser.is_valid(raise_exception=True)
        ser.save(user=request.user)

        cfg = ser.instance
        self._recalc_total_price_safe(cfg)

        # ✅ ВАЖНО: в ответ отдаём полный конфиг (со status/total_price)
        return self._response_full_cfg(cfg, http_status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        locked = self._lock_if_not_draft(instance)
        if locked:
            return locked

        ser = self.get_serializer(
            instance, data=request.data, partial=False, context={"request": request}
        )
        ser.is_valid(raise_exception=True)
        ser.save()

        cfg = ser.instance
        self._recalc_total_price_safe(cfg)

        return self._response_full_cfg(cfg, http_status=status.HTTP_200_OK)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        locked = self._lock_if_not_draft(instance)
        if locked:
            return locked

        ser = self.get_serializer(
            instance, data=request.data, partial=True, context={"request": request}
        )
        ser.is_valid(raise_exception=True)
        ser.save()

        cfg = ser.instance
        self._recalc_total_price_safe(cfg)

        return self._response_full_cfg(cfg, http_status=status.HTTP_200_OK)

    # ---------- actions ----------
    @action(detail=True, methods=["get"])
    def validate(self, request, pk=None):
        configuration = self.get_object()

        is_valid = True
        errors = []

        try:
            validate_configuration_for_submit(configuration)
        except ValidationError as e:
            is_valid = False
            payload = e.detail or {}
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
            payload = e.detail or {}
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

    @action(detail=False, methods=["get"], url_path="main_categories")
    def main_categories(self, request):
        root = EquipmentCategory.objects.filter(name__iexact="Оборудование").first()

        if root:
            qs = EquipmentCategory.objects.filter(parent=root, is_active=True)
        else:
            qs = EquipmentCategory.objects.filter(parent__isnull=True, is_active=True)

        qs = qs.exclude(name__iexact="Оборудование")

        qs = (
            qs.order_by("display_order", "name")
            if hasattr(EquipmentCategory, "display_order")
            else qs.order_by("name")
        )

        data = []
        for c in qs:
            data.append(
                {
                    "id": c.id,
                    "name": c.name,
                    "parent_name": (
                        c.parent.name if getattr(c, "parent_id", None) else "-"
                    ),
                    "equipment_type": getattr(c, "equipment_type", ""),
                    "description": getattr(c, "description", "") or "",
                    "is_active": getattr(c, "is_active", True),
                }
            )
        return Response(data)

    @action(detail=False, methods=["get"])
    def sub_categories(self, request):
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

        subs = EquipmentCategory.objects.filter(parent=main_category, is_active=True)

        subs = (
            subs.order_by("display_order", "id")
            if hasattr(EquipmentCategory, "display_order")
            else subs.order_by("id")
        )

        data = []
        for sub in subs:
            data.append(
                {
                    "id": sub.id,
                    "name": sub.name,
                    "code": getattr(sub, "code", ""),
                    "description": getattr(sub, "description", "") or "",
                    "is_active": getattr(sub, "is_active", True),
                    "parent_name": (
                        sub.parent.name if getattr(sub, "parent_id", None) else "-"
                    ),
                }
            )
        return Response(data)

    @action(detail=False, methods=["get"])
    def available_modules(self, request):
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
                    "physical_type": (
                        module.physical_type.name if module.physical_type else ""
                    ),
                    "applicable_to": getattr(module, "applicable_to", ""),
                }
            )
        return Response(data)

    @action(detail=True, methods=["post"])
    def set_engineering(self, request, pk=None):
        configuration = self.get_object()

        if configuration.status != Configuration.Status.DRAFT:
            return Response(
                {"detail": "Engineering systems can be changed only in DRAFT status."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ser = ConfigurationSetEngineeringSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ids = ser.validated_data["engineering_option_ids"]

        ConfigurationEngineeringSystem.objects.filter(
            configuration=configuration
        ).delete()

        opts = EngineeringSystemOption.objects.filter(
            id__in=ids, is_active=True
        ).select_related("group")
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

        self._recalc_total_price_safe(configuration)

        data = ConfigurationSerializer(configuration, context={"request": request}).data
        data["engineering_option_ids"] = ids
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
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
