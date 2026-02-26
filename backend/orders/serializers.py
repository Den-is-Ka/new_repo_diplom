from rest_framework import serializers

from .models import Order, OrderStatus, OrderStatusHistory


class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class AssignManagerSerializer(serializers.Serializer):
    manager_id = serializers.IntegerField()


class ChangeStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=OrderStatus.choices)
    comment = serializers.CharField(required=False, allow_blank=True)


class OrderStatusHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderStatusHistory
        fields = (
            "id",
            "order",
            "from_status",
            "to_status",
            "comment",
            "changed_by",
            "created_at",
        )
        read_only_fields = fields
