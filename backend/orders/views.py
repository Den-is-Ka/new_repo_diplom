from django.contrib.auth import get_user_model
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from users.roles import is_manufacturer

from .models import Order, OrderStatusHistory
from .permissions import IsOrderOwnerOrStaff
from .serializers import (
    AssignManagerSerializer,
    ChangeStatusSerializer,
    OrderSerializer,
    OrderStatusHistorySerializer,
)
from .services import assign_manager, change_status


class OrderViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    """
    - GET  /api/orders/orders/                 list (staff: all, manufacturer: all, user: own) + ?status=
    - GET  /api/orders/orders/{id}/            retrieve
    - GET  /api/orders/orders/my/              list only my orders (explicit) + ?status=
    - GET  /api/orders/orders/manager/         manager list (staff only) + ?status=
    - POST /api/orders/orders/{id}/assign_manager/   (staff only)
    - POST /api/orders/orders/{id}/change_status/    (staff or manufacturer)
    - GET  /api/orders/orders/{id}/history/          status history
    """

    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated, IsOrderOwnerOrStaff]

    def get_queryset(self):
        # ✅ фикс для drf-spectacular (генерация схемы)
        if getattr(self, "swagger_fake_view", False):
            return Order.objects.none()

        qs = (
            Order.objects.all()
            .select_related("user", "manager", "configuration")
            .order_by("-id")
        )
        user = self.request.user

        if not (user.is_staff or is_manufacturer(user)):
            qs = qs.filter(user=user)

        st = self.request.query_params.get("status")
        if st:
            qs = qs.filter(status=st)

        return qs

    @action(detail=False, methods=["get"], url_path="my")
    def my(self, request):
        """
        Всегда строго "только мои", даже если staff/manufacturer (удобно для UI).
        """
        qs = (
            Order.objects.all()
            .select_related("user", "manager", "configuration")
            .order_by("-id")
            .filter(user=request.user)
        )

        st = request.query_params.get("status")
        if st:
            qs = qs.filter(status=st)

        return Response(self.get_serializer(qs, many=True).data)

    @action(detail=False, methods=["get"], url_path="manager")
    def manager(self, request):
        """
        Менеджерский эндпоинт (MVP: manager = staff).
        """
        if not request.user.is_staff:
            return Response(
                {"detail": "Only manager/staff can access."},
                status=status.HTTP_403_FORBIDDEN,
            )

        qs = (
            Order.objects.all()
            .select_related("user", "manager", "configuration")
            .order_by("-id")
        )

        st = request.query_params.get("status")
        if st:
            qs = qs.filter(status=st)

        return Response(self.get_serializer(qs, many=True).data)

    @action(detail=True, methods=["post"], url_path="assign_manager")
    def assign_manager_action(self, request, pk=None):
        """
        Назначение менеджера — только staff.
        """
        if not request.user.is_staff:
            return Response(
                {"detail": "Only manager/staff can assign manager."},
                status=status.HTTP_403_FORBIDDEN,
            )

        order = self.get_object()

        s = AssignManagerSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        manager_id = s.validated_data["manager_id"]

        User = get_user_model()
        try:
            manager_user = User.objects.get(id=manager_id)
        except User.DoesNotExist:
            return Response(
                {"detail": "Manager user not found."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            updated = assign_manager(
                order_id=order.id, manager_user=manager_user, actor=request.user
            )
        except (ValueError, PermissionError) as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(self.get_serializer(updated).data)

    @action(detail=True, methods=["post"], url_path="change_status")
    def change_status_action(self, request, pk=None):
        """
        Смена статуса — staff или manufacturer.
        """
        if not (request.user.is_staff or is_manufacturer(request.user)):
            return Response(
                {"detail": "Only manager/staff or manufacturer can change status."},
                status=status.HTTP_403_FORBIDDEN,
            )

        order = self.get_object()

        s = ChangeStatusSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        new_status = s.validated_data["status"]
        comment = s.validated_data.get("comment", "")

        try:
            updated = change_status(
                order_id=order.id,
                actor=request.user,
                new_status=new_status,
                comment=comment,
            )
        except PermissionError as e:
            return Response({"detail": str(e)}, status=status.HTTP_403_FORBIDDEN)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(self.get_serializer(updated).data)

    @action(detail=True, methods=["get"], url_path="history")
    def history(self, request, pk=None):
        """
        История статусов.
        Показываем в порядке возрастания времени (как хронология).
        """
        order = self.get_object()
        qs = (
            OrderStatusHistory.objects.filter(order_id=order.id)
            .select_related("changed_by")
            .order_by("created_at")
        )
        return Response(OrderStatusHistorySerializer(qs, many=True).data)
