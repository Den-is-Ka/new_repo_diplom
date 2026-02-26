from rest_framework.permissions import SAFE_METHODS, BasePermission

from users.roles import is_manufacturer


class IsOrderOwnerOrStaff(BasePermission):
    """
    День 1 (P0):
    - Staff (manager/admin) видит и читает все.
    - Manufacturer (группа manufacturer) видит и читает все.
    - Клиент видит/читает только свои заказы.
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.is_staff or is_manufacturer(user):
            return True
        return getattr(obj, "user_id", None) == user.id
