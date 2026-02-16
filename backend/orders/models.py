from django.conf import settings
from django.db import models


class OrderStatus(models.TextChoices):
    NEW = 'NEW', 'New'
    PROCESSING = 'PROCESSING', 'Processing'
    QUOTED = 'QUOTED', 'Quoted'
    COMPLETED = 'COMPLETED', 'Completed'
    CANCELLED = 'CANCELLED', 'Cancelled'


class Order(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='orders',
    )

    # конфигурация может быть удалена/очищена, а заказ должен жить
    configuration = models.ForeignKey(
        'configurator.Configuration',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders',
    )

    order_number = models.CharField(max_length=32, unique=True)
    status = models.CharField(max_length=16, choices=OrderStatus.choices, default=OrderStatus.NEW)

    total_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    snapshot = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-id']

    def __str__(self):
        return f'{self.order_number} ({self.status})'
