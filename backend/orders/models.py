from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone


class OrderStatus(models.TextChoices):
    NEW = "NEW", "New"
    IN_REVIEW = "IN_REVIEW", "In review"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"
    IN_PRODUCTION = "IN_PRODUCTION", "In production"
    COMPLETED = "COMPLETED", "Completed"


# ✅ Строгий жизненный цикл (разрешенные переходы)
ALLOWED_STATUS_TRANSITIONS: dict[str, set[str]] = {
    OrderStatus.NEW: {OrderStatus.IN_REVIEW},
    OrderStatus.IN_REVIEW: {OrderStatus.APPROVED, OrderStatus.REJECTED},
    OrderStatus.APPROVED: {OrderStatus.IN_PRODUCTION},
    OrderStatus.IN_PRODUCTION: {OrderStatus.COMPLETED},
    OrderStatus.REJECTED: set(),  # терминальный
    OrderStatus.COMPLETED: set(),  # терминальный
}

TERMINAL_STATUSES: set[str] = {OrderStatus.REJECTED, OrderStatus.COMPLETED}


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
        db_index=True,
    )

    total_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    snapshot = models.JSONField(default=dict, blank=True)

    # бизнес-фиксация дат статусов
    quoted_at = models.DateTimeField(
        null=True, blank=True
    )  # когда заказ согласован (APPROVED)
    completed_at = models.DateTimeField(
        null=True, blank=True
    )  # когда заказ завершён (COMPLETED)

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
            # Уникальность для configuration (кроме NULL)
            # (у OneToOne и так unique, но этот constraint не ломает и защищает поведение явно)
            models.UniqueConstraint(
                fields=["configuration"],
                condition=models.Q(configuration__isnull=False),
                name="uniq_order_configuration_not_null",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.order_number} ({self.status})"

    # --------- lifecycle helpers ---------

    @property
    def is_terminal(self) -> bool:
        return self.status in TERMINAL_STATUSES

    def can_transition_to(self, new_status: str) -> bool:
        # защита от мусорных статусов
        if new_status not in OrderStatus.values:
            return False
        return new_status in ALLOWED_STATUS_TRANSITIONS.get(self.status, set())

    def transition_to(self, new_status: str) -> None:
        """
        Меняет статус + выставляет бизнес-даты.
        Историю (OrderStatusHistory) логируем в сервисе/вьюхе —
        чтобы туда передать changed_by/comment.
        """
        if self.status == new_status:
            return

        if not self.can_transition_to(new_status):
            raise ValueError(
                f"Invalid status transition: {self.status} -> {new_status}"
            )

        now = timezone.now()
        if new_status == OrderStatus.APPROVED and self.quoted_at is None:
            self.quoted_at = now
        if new_status == OrderStatus.COMPLETED and self.completed_at is None:
            self.completed_at = now

        self.status = new_status


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
            models.Index(fields=["order", "created_at"]),  # важно для /history/
            models.Index(fields=["to_status"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        return f"Order {self.order_id}: {self.from_status} -> {self.to_status}"
