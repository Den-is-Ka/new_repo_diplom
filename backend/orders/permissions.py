from rest_framework.permissions import BasePermission


from rest_framework.permissions import BasePermission


class IsOrderOwnerOrStaff(BasePermission):
    """
    Staff: доступ ко всем заказам.
    Owner: только к своим заказам (Order.user).
    """

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_staff:
            return True
        return getattr(obj, "user_id", None) == user.id

class IsOrderOwnerOrStaff(BasePermission):
    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        return user.is_staff or obj.user_id == user.id