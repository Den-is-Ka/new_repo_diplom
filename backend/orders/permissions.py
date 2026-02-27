from rest_framework.permissions import BasePermission

from users.roles import can_manage_orders


class IsOrderOwnerOrStaff(BasePermission):
    """
    - Admin/staff видит и читает все.
    - Manager (is_manager=True) видит и читает все.
    - Manufacturer (группа manufacturer) видит и читает все.
    - Клиент видит/читает только свои заказы.
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        user = request.user
        if can_manage_orders(user):
            return True
        return getattr(obj, "user_id", None) == user.id
