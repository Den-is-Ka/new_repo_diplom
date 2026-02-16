from rest_framework import serializers
from .models import Order


class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = [
            "id",
            "configuration",
            "user",
            "order_number",
            "status",
            "company_name",
            "phone",
            "email",
            "total_price",
            "snapshot",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "user",
            "order_number",
            "total_price",
            "snapshot",
            "created_at",
            "updated_at",
        ]
