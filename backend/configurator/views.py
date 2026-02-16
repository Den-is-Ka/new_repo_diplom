# backend/configurator/views.py
from django.db import transaction
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from orders.services import create_order_from_configuration

from .models import Configuration
from .serializers import ConfigurationSerializer
from .services.compatibility import validate_configuration


class IsOwnerOrStaff(permissions.BasePermission):
    def has_object_permission(self, request, view, obj: Configuration):
        if request.user and request.user.is_staff:
            return True
        return request.user.is_authenticated and obj.user_id == request.user.id


class ConfigurationViewSet(viewsets.ModelViewSet):
    serializer_class = ConfigurationSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrStaff]

    def get_queryset(self):
        qs = Configuration.objects.all().order_by("-created_at")
        if self.request.user.is_staff:
            return qs
        return qs.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    # -------------------------
    # Helpers
    # -------------------------
    def _collect_issues(self, cfg: Configuration) -> list[dict]:
        issues: list[dict] = []

        if not cfg.sub_category_id:
            issues.append({"level": "error", "code": "NO_SUBCATEGORY", "message": "Sub category is not selected"})

        if cfg.module_items.count() == 0:
            issues.append({"level": "warning", "code": "NO_MODULES", "message": "No modules selected"})

        res = validate_configuration(cfg)
        issues.extend(res.issues)
        return issues

    def _is_ok(self, issues: list[dict]) -> bool:
        return not any(i.get("level") == "error" for i in issues)

    # -------------------------
    # Actions
    # -------------------------
    @action(detail=True, methods=["post"])
    def calculate(self, request, pk=None):
        cfg = self.get_object()
        total = cfg.calculate_total_price()
        if cfg.total_price != total:
            cfg.total_price = total
            cfg.save(update_fields=["total_price", "updated_at"])
        return Response({"id": cfg.id, "total_price": str(cfg.total_price)})

    @action(detail=True, methods=["post"])
    def validate(self, request, pk=None):
        cfg = self.get_object()
        issues = self._collect_issues(cfg)
        ok = self._is_ok(issues)
        return Response({"id": cfg.id, "ok": ok, "issues": issues})

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        """
        1) Валидируем
        2) Переводим конфиг в SUBMITTED (генерится cfg.order_number)
        3) Создаём Order (снимок) идемпотентно: (order, created)
        """
        cfg = self.get_object()

        issues = self._collect_issues(cfg)
        if not self._is_ok(issues):
            return Response(
                {"id": cfg.id, "ok": False, "issues": issues},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            # важно: блокируем строку конфига от гонок двух submit
            cfg = Configuration.objects.select_for_update().get(pk=cfg.pk)

            # гарантируем SUBMITTED (и генерацию order_number)
            if cfg.status != Configuration.Status.SUBMITTED:
                cfg.status = Configuration.Status.SUBMITTED
                # update_fields тут ок, НО: у тебя order_number генерится внутри save()
                # поэтому лучше без update_fields, чтобы код генерации отработал гарантированно
                cfg.save()
            else:
                # если уже submitted — всё равно дернем save() (на случай пустого order_number)
                cfg.save()

            cfg.refresh_from_db(fields=["order_number", "status", "updated_at"])

            order, created = create_order_from_configuration(cfg)

        return Response(
            {
                "ok": True,
                "issues": issues,
                "configuration_id": cfg.id,
                "order_id": order.id,
                "order_number": order.order_number,
                "already_exists": (not created),
            },
            status=(status.HTTP_201_CREATED if created else status.HTTP_200_OK),
        )
