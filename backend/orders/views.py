from django.contrib.auth import get_user_model
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Order, OrderStatusHistory
from .permissions import IsOrderOwnerOrStaff
from .serializers import (
    AssignManagerSerializer,
    ChangeStatusSerializer,
    OrderSerializer,
    OrderStatusHistorySerializer,
)
from .services import assign_manager, change_status


class OrderViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """
    - GET  /api/orders/orders/                 list (staff: all, user: own)
    - GET  /api/orders/orders/{id}/            retrieve
    - GET  /api/orders/orders/my/              list only my orders (explicit)
    - GET  /api/orders/orders/manager/         manager list (staff only) + filter ?status=
    - POST /api/orders/orders/{id}/assign_manager/
    - POST /api/orders/orders/{id}/change_status/
    - GET  /api/orders/orders/{id}/history/    status history
    """
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated, IsOrderOwnerOrStaff]

    def get_queryset(self):
        qs = Order.objects.all().order_by("-id")
        user = self.request.user
        if user.is_staff:
            return qs
        return qs.filter(user=user)

    @action(detail=False, methods=["get"], url_path="my")
    def my(self, request):
        # строго "только мои" — даже если staff
        qs = Order.objects.all().order_by("-id").filter(user=request.user)
        return Response(self.get_serializer(qs, many=True).data)

    @action(detail=False, methods=["get"], url_path="manager")
    def manager(self, request):
        # MVP: менеджер = staff
        if not request.user.is_staff:
            return Response({"detail": "Only manager/staff can access."}, status=status.HTTP_403_FORBIDDEN)

        qs = Order.objects.all().order_by("-id")
        st = request.query_params.get("status")
        if st:
            qs = qs.filter(status=st)

        return Response(self.get_serializer(qs, many=True).data)

    @action(detail=True, methods=["post"], url_path="assign_manager")
    def assign_manager_action(self, request, pk=None):
        if not request.user.is_staff:
            return Response({"detail": "Only manager/staff can assign manager."}, status=status.HTTP_403_FORBIDDEN)

        order = self.get_object()

        s = AssignManagerSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        manager_id = s.validated_data["manager_id"]

        User = get_user_model()
        try:
            manager_user = User.objects.get(id=manager_id)
        except User.DoesNotExist:
            return Response({"detail": "Manager user not found."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            updated = assign_manager(order_id=order.id, manager_user=manager_user, actor=request.user)
        except (ValueError, PermissionError) as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(self.get_serializer(updated).data)

    @action(detail=True, methods=["post"], url_path="change_status")
    def change_status_action(self, request, pk=None):
        if not request.user.is_staff:
            return Response({"detail": "Only manager/staff can change status."}, status=status.HTTP_403_FORBIDDEN)

        order = self.get_object()

        s = ChangeStatusSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        new_status = s.validated_data["status"]
        comment = s.validated_data.get("comment", "")

        try:
            updated = change_status(order_id=order.id, actor=request.user, new_status=new_status, comment=comment)
        except PermissionError as e:
            return Response({"detail": str(e)}, status=status.HTTP_403_FORBIDDEN)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(self.get_serializer(updated).data)

    @action(detail=True, methods=["get"], url_path="history")
    def history(self, request, pk=None):
        # доступ контролируется IsOrderOwnerOrStaff через self.get_object()
        order = self.get_object()
        qs = OrderStatusHistory.objects.filter(order_id=order.id).order_by("created_at")
        return Response(OrderStatusHistorySerializer(qs, many=True).data)
