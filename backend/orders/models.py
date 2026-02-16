from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Order(models.Model):
    class Status(models.TextChoices):
        NEW = "new", _("Новый")
        PROCESSING = "processing", _("В обработке")
        QUOTED = "quoted", _("Счет выставлен")
        COMPLETED = "completed", _("Завершен")
        CANCELED = "canceled", _("Отменен")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="orders",
        verbose_name=_("Пользователь"),
    )

    # Ключевая часть идемпотентности:
    # один Configuration -> один Order (DB-level гарантия)
    configuration = models.OneToOneField(
        "configurator.Configuration",
        on_delete=models.PROTECT,
        related_name="order",
    )

    order_number = models.CharField(
        _("Номер заказа"),
        max_length=50,
        unique=True,
    )

    status = models.CharField(
        _("Статус"),
        max_length=20,
        choices=Status.choices,
        default=Status.NEW,
    )

    company_name = models.CharField(_("Название предприятия"), max_length=200, blank=True)
    phone = models.CharField(_("Телефон"), max_length=20, blank=True)
    email = models.EmailField(_("Email"), blank=True)

    total_price = models.DecimalField(
        _("Итоговая стоимость (снимок)"),
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    snapshot = models.JSONField(
        _("Снимок заказа"),
        default=dict,
        blank=True,
    )

    created_at = models.DateTimeField(_("Дата создания"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Дата обновления"), auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Заказ")
        verbose_name_plural = _("Заказы")

    def __str__(self):
        return f"{self.order_number} ({self.get_status_display()})"
