from rest_framework import permissions, viewsets

from .models import Order
from .serializers import OrderSerializer


class IsOwnerOrStaff(permissions.BasePermission):
    def has_object_permission(self, request, view, obj: Order):
        if request.user and request.user.is_staff:
            return True
        return request.user.is_authenticated and obj.user_id == request.user.id


class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrStaff]

    def get_queryset(self):
        qs = Order.objects.all().select_related("user", "configuration").order_by("-created_at")
        if self.request.user.is_staff:
            return qs
        return qs.filter(user=self.request.user)

    def perform_create(self, serializer):
        # обычно мы НЕ создаем заказ руками через API — он создается submit-ом.
        # но если оставляешь create — хотя бы привяжем user.
        serializer.save(user=self.request.user)
