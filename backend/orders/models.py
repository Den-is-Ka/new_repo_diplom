from django.conf import settings
from django.db import models


class OrderStatus(models.TextChoices):
    NEW = "NEW", "New"
    IN_REVIEW = "IN_REVIEW", "In review"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"
    IN_PRODUCTION = "IN_PRODUCTION", "In production"
    COMPLETED = "COMPLETED", "Completed"


class Order(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="orders",
    )

    # менеджер, который ведёт заказ (назначается после submit)
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_orders",
    )

    # 1 конфигурация -> 1 заказ (идемпотентный submit)
    # конфигурация может быть удалена, а заказ должен жить
    configuration = models.OneToOneField(
        "configurator.Configuration",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order",
    )

    order_number = models.CharField(max_length=32, unique=True)

    status = models.CharField(
        max_length=16,
        choices=OrderStatus.choices,
        default=OrderStatus.NEW,
    )

    total_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    snapshot = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-id"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["manager", "status"]),
            models.Index(fields=["user", "status"]),
        ]
        constraints = [
            # Явно фиксируем уникальность для configuration (кроме NULL)
            models.UniqueConstraint(
                fields=["configuration"],
                condition=models.Q(configuration__isnull=False),
                name="uniq_order_configuration_not_null",
            ),
        ]

    def __str__(self):
        return f"{self.order_number} ({self.status})"


class OrderStatusHistory(models.Model):
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.CASCADE,
        related_name="status_history",
    )

    from_status = models.CharField(max_length=16, choices=OrderStatus.choices)
    to_status = models.CharField(max_length=16, choices=OrderStatus.choices)

    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_status_changes",
    )

    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["order", "created_at"]),   # важно для /history/
            models.Index(fields=["to_status"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"Order {self.order_id}: {self.from_status} -> {self.to_status}"
