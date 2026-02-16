from django.contrib import admin
from .models import Order


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "order_number",
        "status",
        "user",
        "configuration",
        "company_name",
        "total_price",
        "created_at",
    )
    list_filter = ("status", "created_at")
    search_fields = ("order_number", "company_name", "email", "phone")
    readonly_fields = ("order_number", "snapshot", "created_at", "updated_at")
