from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """астомная админка для пользователей"""

    list_display = ("username", "email", "first_name", "last_name", "is_staff", "phone")
    fieldsets = UserAdmin.fieldsets + (
        ("ополнительная информация", {"fields": ("phone",)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("ополнительная информация", {"fields": ("phone",)}),
    )
