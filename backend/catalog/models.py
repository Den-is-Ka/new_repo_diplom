from django.db import models
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _


class EquipmentType(models.Model):
    """Тип оборудования (категория)"""
    name = models.CharField(_("Название типа"), max_length=100, unique=True)
    description = models.TextField(_("Описание"), blank=True)
    image = models.ImageField(_("Изображение"), upload_to='equipment_types/', blank=True, null=True)
    order = models.PositiveIntegerField(_("Порядок отображения"), default=0)

    class Meta:
        ordering = ['order', 'name']
        verbose_name = _("Тип оборудования")
        verbose_name_plural = _("Типы оборудования")

    def __str__(self):
        return self.name


class EquipmentModule(models.Model):
    """Модуль оборудования"""

    class PriceType(models.TextChoices):
        FIXED = 'fixed', _("Фиксированная цена")
        INDIVIDUAL = 'individual', _("Индивидуальный расчёт")
        UPON_REQUEST = 'request', _("По запросу")

    name = models.CharField(_("Название модуля"), max_length=200)
    equipment_type = models.ForeignKey(
        EquipmentType,
        on_delete=models.CASCADE,
        related_name='modules',
        verbose_name=_("Тип оборудования")
    )
    description = models.TextField(_("Описание"), blank=True)

    # Цена
    price_type = models.CharField(
        _("Тип цены"),
        max_length=20,
        choices=PriceType.choices,
        default=PriceType.FIXED
    )
    price = models.DecimalField(
        _("Цена"),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        blank=True,
        null=True,
        help_text=_("Заполняется только если price_type='fixed'")
    )

    # Изображения
    main_image = models.ImageField(_("Основное изображение"), upload_to='modules/', blank=True, null=True)

    # Технические характеристики (можно расширять)
    power_consumption = models.IntegerField(_("Потребляемая мощность, Вт"), blank=True, null=True)
    dimensions = models.CharField(_("Габариты (ШхВхГ)"), max_length=100, blank=True)
    weight = models.DecimalField(_("Вес, кг"), max_digits=8, decimal_places=2, blank=True, null=True)

    # Флаги для логики
    is_active = models.BooleanField(_("Активен"), default=True)
    is_default = models.BooleanField(_("Выбран по умолчанию"), default=False)

    # Взаимоисключения будут обрабатываться отдельной моделью
    created_at = models.DateTimeField(_("Дата создания"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Дата обновления"), auto_now=True)

    class Meta:
        ordering = ['equipment_type__order', 'name']
        verbose_name = _("Модуль оборудования")
        verbose_name_plural = _("Модули оборудования")
        indexes = [
            models.Index(fields=['is_active', 'equipment_type']),
        ]

    def __str__(self):
        return f"{self.equipment_type.name} - {self.name}"

    @property
    def display_price(self):
        """Форматированное отображение цены"""
        if self.price_type == self.PriceType.FIXED and self.price:
            return f"{self.price:.2f} руб."
        return dict(self.PriceType.choices)[self.price_type]


class CompatibilityRule(models.Model):
    """Правила совместимости модулей"""

    class RuleType(models.TextChoices):
        EXCLUSION = 'exclusion', _("Взаимоисключение")
        REQUIREMENT = 'requirement', _("Требование")
        GROUP = 'group', _("Группа")
        LIMIT = 'limit', _("Ограничение количества")

    name = models.CharField(_("Название правила"), max_length=200)
    rule_type = models.CharField(_("Тип правила"), max_length=20, choices=RuleType.choices)
    description = models.TextField(_("Описание правила"), blank=True)

    # Модули, к которым применяется правило
    modules = models.ManyToManyField(
        EquipmentModule,
        related_name='compatibility_rules',
        verbose_name=_("Модули")
    )

    # Параметры правила
    max_quantity = models.PositiveIntegerField(
        _("Максимальное количество"),
        blank=True,
        null=True,
        help_text=_("Для rule_type='limit'")
    )

    # Для требований: если выбран module A, то нужен module B
    required_module = models.ForeignKey(
        EquipmentModule,
        on_delete=models.CASCADE,
        related_name='required_by_rules',
        verbose_name=_("Требуемый модуль"),
        blank=True,
        null=True,
        help_text=_("Для rule_type='requirement'")
    )

    is_active = models.BooleanField(_("Активно"), default=True)

    class Meta:
        verbose_name = _("Правило совместимости")
        verbose_name_plural = _("Правила совместимости")

    def __str__(self):
        return f"{self.get_rule_type_display()}: {self.name}"
