from django.contrib import admin

try:
    from .models import Order
except Exception:
    Order = None


if Order is not None:

    @admin.register(Order)
    class OrderAdmin(admin.ModelAdmin):
        def get_list_display(self, request):
            candidates = [
                "id",
                "order_number",
                "status",
                "created_at",
                "updated_at",
                "user",
                "configuration",
            ]
            existing = {f.name for f in self.model._meta.fields}
            cols = [c for c in candidates if c in existing]
            return tuple(cols) if cols else ("id",)
