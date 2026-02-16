from django.core.exceptions import FieldDoesNotExist
from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated

from .models import Order
from .serializers import OrderSerializer
from .permissions import IsOrderOwnerOrStaff


def has_field(model, name: str) -> bool:
    """Безопасно проверяем, существует ли поле у модели."""
    try:
        model._meta.get_field(name)
        return True
    except FieldDoesNotExist:
        return False


class OrderViewSet(mixins.ListModelMixin,
                   mixins.RetrieveModelMixin,
                   viewsets.GenericViewSet):
    """
    MVP:
      - GET /api/orders/orders/        (list)
      - GET /api/orders/orders/{id}/   (retrieve)

    Права:
      - staff видит всё
      - пользователь видит только свои (через Order.user)
        fallback: через Order.configuration.user (если вдруг Order.user уберёшь)
    """
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated, IsOrderOwnerOrStaff]

    def get_queryset(self):
        qs = Order.objects.all().order_by("-id")
        user = self.request.user

        # Staff видит всё
        if user.is_staff:
            return qs

        # Основной и правильный путь для твоей текущей модели:
        # Order.user всегда есть -> фильтруем по нему
        if has_field(Order, "user"):
            return qs.filter(user=user)

        # Fallback (на будущее / если модель поменяется):
        # Order.configuration -> Configuration.user
        if has_field(Order, "configuration"):
            cfg_field = Order._meta.get_field("configuration")
            cfg_model = cfg_field.related_model

            if has_field(cfg_model, "user"):
                return qs.filter(**{f"{cfg_field.name}__user": user})

        # Если вообще не можем определить владельца — не показываем ничего
        return qs.none()

