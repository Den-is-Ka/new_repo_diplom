from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class Configuration(models.Model):
    """Конфигурация оборудования пользователя"""

    class Status(models.TextChoices):
        DRAFT = "draft", _("Черновик")
        SUBMITTED = "submitted", _("Отправлен производителю")
        PROCESSING = "processing", _("В обработке")
        QUOTED = "quoted", _("Счет выставлен")
        COMPLETED = "completed", _("Завершен")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="configurations",
        verbose_name=_("Пользователь"),
    )

    main_category = models.ForeignKey(
        "catalog.EquipmentCategory",
        on_delete=models.CASCADE,
        related_name="configurations",
        verbose_name=_("Основной тип оборудования"),
        help_text=_("ДГУ или Компрессорная установка"),
    )

    sub_category = models.ForeignKey(
        "catalog.EquipmentCategory",
        on_delete=models.CASCADE,
        related_name="sub_configurations",
        verbose_name=_("Подкатегория"),
        help_text=_("Конкретная характеристика, например: ДГУ до 50 кВт"),
        null=True,
        blank=True,
    )

    container_config = models.JSONField(
        _("Конфигурация контейнера"),
        default=dict,
        blank=True,
        help_text=_("Параметры контейнера в формате JSON"),
    )

    name = models.CharField(_("Название конфигурации"), max_length=200)
    description = models.TextField(_("Описание"), blank=True)

    modules = models.ManyToManyField(
        "catalog.EquipmentModule",
        through="ConfigurationModule",
        related_name="configurations",
        verbose_name=_("Выбранные модули"),
        blank=True,
    )

    engineering_systems = models.ManyToManyField(
        "catalog.EngineeringSystemOption",
        through="ConfigurationEngineeringSystem",
        related_name="configurations",
        verbose_name=_("Инженерные системы"),
        blank=True,
    )

    total_price = models.DecimalField(
        _("Общая стоимость"),
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    status = models.CharField(
        _("Статус"),
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )

    order_number = models.CharField(
        _("Номер заказа"),
        max_length=50,
        blank=True,
    )

    submitted_at = models.DateTimeField(
        _("Дата отправки"),
        null=True,
        blank=True,
    )

    company_name = models.CharField(
        _("Название предприятия"), max_length=200, blank=True
    )
    phone = models.CharField(_("Телефон"), max_length=20, blank=True)
    email = models.EmailField(_("Email"), blank=True)

    created_at = models.DateTimeField(_("Дата создания"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Дата обновления"), auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Конфигурация")
        verbose_name_plural = _("Конфигурации")

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"

    # ✅ единая проверка “конфиг залочен”: редактировать можно только DRAFT
    def is_locked(self) -> bool:
        return self.status != self.Status.DRAFT

    def calculate_total_price(self) -> Decimal:
        """Расчет общей стоимости (фиксированные цены)"""
        if not self.pk:
            return Decimal("0.00")

        total = Decimal("0.00")

        for item in self.module_items.select_related("module").all():
            m = item.module
            if m.price_type == "fixed" and m.price is not None:
                total += m.price * item.quantity

        for item in self.engineering_items.select_related("engineering_system").all():
            s = item.engineering_system
            if s.price_type == "fixed":
                price = (
                    item.price_at_selection
                    if item.price_at_selection is not None
                    else (s.price or Decimal("0.00"))
                )
                total += price * item.quantity

        return total

    def _validate_locked_update(self, old_status: str | None):
        """
        Запрещаем менять бизнес-поля конфигурации, если она НЕ в DRAFT.

        Разрешаем служебные изменения:
          - status (workflow)
          - order_number (генерация номера)
          - total_price (пересчет)
          - submitted_at (фиксируем при submit)
          - updated_at (служебное)
        """
        if not self.pk:
            return

        # если ранее уже было НЕ DRAFT — конфиг залочен
        if old_status and old_status != self.Status.DRAFT:
            protected_fields = [
                "name",
                "description",
                "container_config",
                "main_category_id",
                "sub_category_id",
                "user_id",
                "company_name",
                "phone",
                "email",
            ]

            old = (
                Configuration.objects.filter(pk=self.pk)
                .only(*protected_fields, "status")
                .first()
            )
            if not old:
                return

            changed = []
            for f in protected_fields:
                if getattr(old, f) != getattr(self, f):
                    changed.append(f)

            if changed:
                raise ValidationError(
                    {
                        "detail": _("Configuration is locked after submit."),
                        "fields": changed,
                    }
                )

    def save(self, *args, **kwargs):
        # 0) определяем старый статус (для lock + фиксации submit transition)
        old_status = None
        if self.pk:
            old_status = (
                Configuration.objects.filter(pk=self.pk)
                .values_list("status", flat=True)
                .first()
            )

        # 1) запрет редактирования бизнес-полей, если раньше был НЕ DRAFT
        self._validate_locked_update(old_status)

        # 2) Автоматически выставляем main_category на основе sub_category
        if self.sub_category and not self.main_category:
            current = self.sub_category
            while current.parent and current.parent.parent:
                current = current.parent
            self.main_category = current

        # 3) сохраняем объект, чтобы появился pk / обновились поля
        super().save(*args, **kwargs)

        # 4) пересчет total_price
        # (после submit через таблицы-сквозняки менять нельзя, так что цена фактически стабильна)
        new_total = self.calculate_total_price()
        if self.total_price != new_total:
            self.total_price = new_total
            super().save(update_fields=["total_price", "updated_at"])

        # 5) при ПЕРЕХОДЕ в SUBMITTED — фиксируем submitted_at и order_number
        transitioned_to_submitted = (old_status != self.Status.SUBMITTED) and (
            self.status == self.Status.SUBMITTED
        )
        if transitioned_to_submitted:
            if self.submitted_at is None:
                self.submitted_at = timezone.now()
                super().save(update_fields=["submitted_at", "updated_at"])

            if not self.order_number:
                date_str = timezone.now().strftime("%Y%m%d")
                # считаем уже существующие SUBMITTED за сегодня (текущая запись уже SUBMITTED, поэтому +1 ок)
                count = Configuration.objects.filter(
                    status=self.Status.SUBMITTED,
                    created_at__date=timezone.now().date(),
                ).count()
                self.order_number = f"ORD-{date_str}-{count:04d}"
                super().save(update_fields=["order_number", "updated_at"])


class ConfigurationModule(models.Model):
    """Выбранный модуль в конфигурации"""

    configuration = models.ForeignKey(
        "configurator.Configuration",
        on_delete=models.CASCADE,
        related_name="module_items",
    )
    module = models.ForeignKey(
        "catalog.EquipmentModule",
        on_delete=models.PROTECT,
        related_name="configuration_items",
    )
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])

    class Meta:
        verbose_name = _("Выбранный модуль")
        verbose_name_plural = _("Выбранные модули")
        constraints = [
            models.UniqueConstraint(
                fields=["configuration", "module"], name="uniq_config_module"
            )
        ]

    def __str__(self):
        return f"{self.module} x{self.quantity}"

    def save(self, *args, **kwargs):
        if self.configuration_id:
            cfg = Configuration.objects.only("status").get(pk=self.configuration_id)
            if cfg.is_locked():
                raise ValidationError(_("Configuration is locked after submit."))
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        cfg = Configuration.objects.only("status").get(pk=self.configuration_id)
        if cfg.is_locked():
            raise ValidationError(_("Configuration is locked after submit."))
        return super().delete(*args, **kwargs)


class ConfigurationEngineeringSystem(models.Model):
    """Выбранная инженерная система в конфигурации"""

    configuration = models.ForeignKey(
        "configurator.Configuration",
        on_delete=models.CASCADE,
        related_name="engineering_items",
    )

    engineering_system = models.ForeignKey(
        "catalog.EngineeringSystemOption",
        on_delete=models.PROTECT,
        related_name="configuration_items",
    )

    quantity = models.PositiveIntegerField(
        _("Количество"),
        default=1,
        validators=[MinValueValidator(1)],
    )

    custom_parameters = models.JSONField(
        _("Пользовательские параметры"),
        null=True,
        blank=True,
        help_text=_("Дополнительные настройки в формате JSON"),
    )

    price_at_selection = models.DecimalField(
        _("Цена на момент выбора"),
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = _("Выбранная инженерная система")
        verbose_name_plural = _("Выбранные инженерные системы")
        constraints = [
            models.UniqueConstraint(
                fields=["configuration", "engineering_system"],
                name="uniq_config_engineering",
            )
        ]

    def __str__(self):
        return f"{self.engineering_system} x{self.quantity}"

    def save(self, *args, **kwargs):
        if self.configuration_id:
            cfg = Configuration.objects.only("status").get(pk=self.configuration_id)
            if cfg.is_locked():
                raise ValidationError(_("Configuration is locked after submit."))

        # фикс “цена на момент выбора”: не сохраняем None для fixed
        if (
            self.price_at_selection is None
            and self.engineering_system.price_type == "fixed"
        ):
            self.price_at_selection = self.engineering_system.price or Decimal("0.00")

        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        cfg = Configuration.objects.only("status").get(pk=self.configuration_id)
        if cfg.is_locked():
            raise ValidationError(_("Configuration is locked after submit."))
        return super().delete(*args, **kwargs)
