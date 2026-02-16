from rest_framework.permissions import BasePermission


class IsOrderOwnerOrStaff(BasePermission):
    """
    staff: доступ ко всем заказам
    user: доступ только к своим заказам

    Основной вариант владения:
      - Order.user

    Fallback на будущее:
      - Order.configuration.user
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.is_staff:
            return True

        owner = getattr(obj, "user", None)
        if owner is not None:
            return owner == user

        cfg = getattr(obj, "configuration", None)
        if cfg is not None:
            cfg_user = getattr(cfg, "user", None)
            return cfg_user == user

        return False
