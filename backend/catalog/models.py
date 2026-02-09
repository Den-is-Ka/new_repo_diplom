from django.db import models
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _


class EquipmentCategory(models.Model):
    """Иерархическая категория оборудования (по ТЗ: 1, 1.1, 1.1.1 и т.д.)"""

    class EquipmentType(models.TextChoices):
        DGU = 'DGU', _("Дизельно-генераторная установка")
        COMPRESSOR = 'COMPRESSOR', _("Компрессорная установка")
        UNIVERSAL = 'UNIVERSAL', _("Универсальный")

    name = models.CharField(_("Название категории"), max_length=200)
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name=_("Родительская категория")
    )
    equipment_type = models.CharField(
        _("Тип оборудования"),
        max_length=20,
        choices=EquipmentType.choices,
        default=EquipmentType.UNIVERSAL
    )
    description = models.TextField(_("Описание"), blank=True)
    order = models.PositiveIntegerField(_("Порядок отображения"), default=0)
    is_active = models.BooleanField(_("Активна"), default=True)

    # Для удобства навигации
    code = models.CharField(_("Код категории"), max_length=50, blank=True, help_text=_("Например: 1.1.1"))

    class Meta:
        ordering = ['order', 'name']
        verbose_name = _("Категория оборудования")
        verbose_name_plural = _("Категории оборудования")
        indexes = [
            models.Index(fields=['parent', 'is_active']),
        ]

    def __str__(self):
        if self.parent:
            return f"{self.parent} > {self.name}"
        return self.name

    def save(self, *args, **kwargs):
        # Автоматически генерируем код на основе иерархии
        if not self.code and self.parent:
            siblings = EquipmentCategory.objects.filter(parent=self.parent).count()
            self.code = f"{self.parent.code}.{siblings + 1}"
        elif not self.code and not self.parent:
            # Корневая категория
            roots = EquipmentCategory.objects.filter(parent__isnull=True).count()
            self.code = str(roots + 1)
        super().save(*args, **kwargs)

    @property
    def is_root(self):
        return self.parent is None

    @property
    def is_leaf(self):
        return not self.children.exists()

    @property
    def full_path(self):
        """Полный путь категории"""
        path = []
        current = self
        while current:
            path.insert(0, current.name)
            current = current.parent
        return " > ".join(path)


# Оставляем существующий EquipmentType как "физический тип оборудования"
# но переименуем его, чтобы не путать с EquipmentCategory
class EquipmentPhysicalType(models.Model):
    """Физический тип оборудования (Процессор, Материнская плата и т.д.)"""
    name = models.CharField(_("Название типа"), max_length=100, unique=True)
    description = models.TextField(_("Описание"), blank=True)
    image = models.ImageField(_("Изображение"), upload_to='equipment_types/', blank=True, null=True)
    order = models.PositiveIntegerField(_("Порядок отображения"), default=0)

    # К какой категории ТЗ относится (ДГУ, Компрессор, Универсальный)
    applicable_category = models.CharField(
        _("Применимость"),
        max_length=20,
        choices=EquipmentCategory.EquipmentType.choices,
        default=EquipmentCategory.EquipmentType.UNIVERSAL
    )

    class Meta:
        ordering = ['order', 'name']
        verbose_name = _("Физический тип оборудования")
        verbose_name_plural = _("Физические типы оборудования")

    def __str__(self):
        return self.name


class EquipmentModule(models.Model):
    """Модуль оборудования"""

    class PriceType(models.TextChoices):
        FIXED = 'fixed', _("Фиксированная цена")
        INDIVIDUAL = 'individual', _("Индивидуальный расчёт")
        UPON_REQUEST = 'request', _("По запросу")

    class ApplicableTo(models.TextChoices):
        DGU = 'DGU', _("Только для ДГУ")
        COMPRESSOR = 'COMPRESSOR', _("Только для компрессоров")
        BOTH = 'BOTH', _("Универсальный (для обоих)")

    name = models.CharField(_("Название модуля"), max_length=200)

    # Две связи:
    # 1. К какой категории ТЗ относится (1.1.1, 1.2.2 и т.д.)
    category = models.ForeignKey(
        EquipmentCategory,
        on_delete=models.CASCADE,
        related_name='modules_by_category',
        verbose_name=_("Категория ТЗ"),
        help_text=_("Выберите категорию из иерархии ТЗ")
    )

    # 2. К какому физическому типу относится
    physical_type = models.ForeignKey(
        EquipmentPhysicalType,
        on_delete=models.CASCADE,
        related_name='modules_by_type',
        verbose_name=_("Физический тип"),
        help_text=_("Физический тип оборудования")
    )

    # Применимость (для фильтрации)
    applicable_to = models.CharField(
        _("Применимость к оборудованию"),
        max_length=20,
        choices=ApplicableTo.choices,
        default=ApplicableTo.BOTH
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

    # Технические характеристики
    power_consumption = models.IntegerField(_("Потребляемая мощность, Вт"), blank=True, null=True)
    dimensions = models.CharField(_("Габариты (ШхВхГ)"), max_length=100, blank=True)
    weight = models.DecimalField(_("Вес, кг"), max_digits=8, decimal_places=2, blank=True, null=True)

    # Дополнительные характеристики в JSON
    specifications = models.JSONField(
        _("Технические характеристики"),
        default=dict,
        blank=True,
        help_text=_("Дополнительные характеристики в формате JSON")
    )

    # Флаги
    is_active = models.BooleanField(_("Активен"), default=True)
    is_default = models.BooleanField(_("Выбран по умолчанию"), default=False)

    created_at = models.DateTimeField(_("Дата создания"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Дата обновления"), auto_now=True)

    class Meta:
        ordering = ['category__order', 'physical_type__order', 'name']
        verbose_name = _("Модуль оборудования")
        verbose_name_plural = _("Модули оборудования")
        indexes = [
            models.Index(fields=['is_active', 'category', 'applicable_to']),
        ]

    def __str__(self):
        return f"{self.category.name} - {self.name}"

    @property
    def display_price(self):
        """Форматированное отображение цены"""
        if self.price_type == self.PriceType.FIXED and self.price:
            return f"{self.price:.2f} руб."
        return dict(self.PriceType.choices)[self.price_type]

    def is_compatible_with(self, equipment_type):
        """
        Проверка совместимости с типом оборудования
        equipment_type: 'DGU' или 'COMPRESSOR'
        """
        if self.applicable_to == 'BOTH':
            return True
        return self.applicable_to == equipment_type


class CompatibilityRule(models.Model):
    """Правила совместимости модулей"""

    class RuleType(models.TextChoices):
        EXCLUSION = 'exclusion', _("Взаимоисключение")
        REQUIREMENT = 'requirement', _("Требование")
        GROUP = 'group', _("Группа")
        LIMIT = 'limit', _("Ограничение количества")
        CATEGORY_EXCLUSION = 'category_exclusion', _("Исключение по категории")

    name = models.CharField(_("Название правила"), max_length=200)
    rule_type = models.CharField(_("Тип правила"), max_length=20, choices=RuleType.choices)
    description = models.TextField(_("Описание правила"), blank=True)

    # Для категорийной логики (из ТЗ: если выбран 1.1, то 1.2 недоступен)
    category = models.ForeignKey(
        EquipmentCategory,
        on_delete=models.CASCADE,
        related_name='category_rules',
        verbose_name=_("Категория"),
        blank=True,
        null=True,
        help_text=_("Для правил, связанных с категориями")
    )

    excluded_categories = models.ManyToManyField(
        EquipmentCategory,
        related_name='excluded_by_rules',
        verbose_name=_("Исключаемые категории"),
        blank=True,
        help_text=_("Категории, которые становятся недоступными при выборе указанной категории")
    )

    # Модули, к которым применяется правило
    modules = models.ManyToManyField(
        EquipmentModule,
        related_name='compatibility_rules',
        verbose_name=_("Модули"),
        blank=True
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


class ContainerConfiguration(models.Model):
    """Конфигурация контейнера (раздел 3 ТЗ)"""

    # 3.1) Габаритные размеры контейнера
    class Height(models.TextChoices):
        HEIGHT_1800 = '1800', '1800 мм'
        HEIGHT_2200 = '2200', '2200 мм'
        HEIGHT_2600 = '2600', '2600 мм'
        HEIGHT_3000 = '3000', '3000 мм'
        HEIGHT_3400 = '3400', '3400 мм'

    class Length(models.TextChoices):
        LENGTH_4000 = '4000', '4000 мм'
        LENGTH_6000 = '6000', '6000 мм'
        LENGTH_9000 = '9000', '9000 мм'
        LENGTH_12000 = '12000', '12000 мм'
        LENGTH_14000 = '14000', '14000 мм'

    class Width(models.TextChoices):
        WIDTH_1500 = '1500', '1500 мм'
        WIDTH_2000 = '2000', '2000 мм'
        WIDTH_2500 = '2500', '2500 мм'
        WIDTH_3000 = '3000', '3000 мм'
        WIDTH_3400 = '3400', '3400 мм'

    height = models.CharField(
        "Высота",
        max_length=10,
        choices=Height.choices,
        default=Height.HEIGHT_2600
    )

    length = models.CharField(
        "Длина",
        max_length=10,
        choices=Length.choices,
        default=Length.LENGTH_6000
    )

    width = models.CharField(
        "Ширина",
        max_length=10,
        choices=Width.choices,
        default=Width.WIDTH_2500
    )

    # 3.2) Тип исполнения контейнера
    class ContainerType(models.TextChoices):
        METAL = 'metal', 'Цельнометаллический'
        SANDWICH = 'sandwich', 'Каркасный + сендвич панели'

    container_type = models.CharField(
        "Тип исполнения контейнера",
        max_length=20,
        choices=ContainerType.choices,
        default=ContainerType.METAL
    )

    # 3.3) Требуемая степень огнестойкости
    class FireResistance(models.TextChoices):
        GROUP_IV = 'IV', 'Группа огнестойкости IV'
        GROUP_III = 'III', 'Группа огнестойкости III'
        GROUP_II = 'II', 'Группа огнестойкости II'

    fire_resistance = models.CharField(
        "Степень огнестойкости",
        max_length=10,
        choices=FireResistance.choices,
        default=FireResistance.GROUP_III
    )

    # 3.4) Основание контейнера
    class InsulationThickness(models.TextChoices):
        THICK_100 = '100', '100 мм'
        THICK_150 = '150', '150 мм'
        OTHER = 'other', 'Другое'

    floor_insulation_thickness = models.CharField(
        "Толщина утеплителя пола",
        max_length=10,
        choices=InsulationThickness.choices,
        default=InsulationThickness.THICK_100
    )

    class FloorSheetThickness(models.TextChoices):
        THICK_3 = '3', '3 мм'
        THICK_4 = '4', '4 мм'
        OTHER = 'other', 'Другое'

    floor_sheet_thickness = models.CharField(
        "Толщина листа настила пола",
        max_length=10,
        choices=FloorSheetThickness.choices,
        default=FloorSheetThickness.THICK_3
    )

    class BottomSheetThickness(models.TextChoices):
        THICK_1_2 = '1.2', '1.2 мм'
        THICK_1_5 = '1.5', '1.5 мм'
        THICK_2 = '2', '2 мм'

    bottom_sheet_thickness = models.CharField(
        "Толщина подшивки дна основания",
        max_length=10,
        choices=BottomSheetThickness.choices,
        default=BottomSheetThickness.THICK_1_5
    )

    class AdditionalFloor(models.TextChoices):
        NONE = 'none', 'Не требуется'
        LINOLEUM = 'linoleum', 'Линолеум'
        ALUMINUM = 'aluminum', 'Алюминиевый лист'

    additional_floor = models.CharField(
        "Дополнительный настил пола",
        max_length=20,
        choices=AdditionalFloor.choices,
        default=AdditionalFloor.NONE
    )

    # 3.5) Крыша контейнера
    roof_insulation_thickness = models.CharField(
        "Толщина утеплителя крыши",
        max_length=10,
        choices=InsulationThickness.choices,
        default=InsulationThickness.THICK_100
    )

    roof_sheet_thickness = models.CharField(
        "Толщина листа настила кровли",
        max_length=10,
        choices=BottomSheetThickness.choices,
        default=BottomSheetThickness.THICK_1_5
    )

    class RoofSlope(models.TextChoices):
        SLOPED = 'sloped', 'Малоуклонная'
        FLAT = 'flat', 'Без уклона'

    roof_slope = models.CharField(
        "Уклон кровли",
        max_length=20,
        choices=RoofSlope.choices,
        default=RoofSlope.SLOPED
    )

    # 3.6) Стены контейнера
    wall_insulation_thickness = models.CharField(
        "Толщина утеплителя стен",
        max_length=10,
        choices=InsulationThickness.choices,
        default=InsulationThickness.THICK_100
    )

    wall_sheet_thickness = models.CharField(
        "Толщина внешней облицовки стен",
        max_length=10,
        choices=BottomSheetThickness.choices,
        default=BottomSheetThickness.THICK_1_5
    )

    class WallPanelType(models.TextChoices):
        PROFILED = 'profiled', 'Профилированный лист'
        FLAT = 'flat', 'Плоская панель'

    wall_panel_type = models.CharField(
        "Тип внешней облицовки стен",
        max_length=20,
        choices=WallPanelType.choices,
        default=WallPanelType.PROFILED
    )

    # 3.7) Эксплуатационное исполнение
    class OperationalType(models.TextChoices):
        GROUND_STATIONARY = 'ground', 'Наземное стационарное'
        HANGING_STATIONARY = 'hanging', 'Подвесное стационарное'
        MOBILE = 'mobile', 'Мобильное на шасси'

    operational_type = models.CharField(
        "Эксплуатационное исполнение",
        max_length=20,
        choices=OperationalType.choices,
        default=OperationalType.GROUND_STATIONARY
    )

    # 3.8) Брендирование
    class Branding(models.TextChoices):
        REQUIRED = 'required', 'Требуется'
        NOT_REQUIRED = 'not_required', 'Не требуется'

    branding = models.CharField(
        "Брендирование (логотип)",
        max_length=20,
        choices=Branding.choices,
        default=Branding.NOT_REQUIRED
    )

    # 3.9) Упаковка
    class Packaging(models.TextChoices):
        REQUIRED = 'required', 'Требуется'
        NOT_REQUIRED = 'not_required', 'Не требуется'

    packaging = models.CharField(
        "Упаковка в транспортную пленку",
        max_length=20,
        choices=Packaging.choices,
        default=Packaging.REQUIRED
    )

    # Дополнительные поля
    name = models.CharField(
        "Название конфигурации",
        max_length=200,
        default="Базовая конфигурация"
    )

    description = models.TextField(
        "Описание",
        blank=True
    )

    base_price = models.DecimalField(
        "Базовая цена контейнера",
        max_digits=12,
        decimal_places=2,
        default=0
    )

    is_active = models.BooleanField(
        "Активна",
        default=True
    )

    is_default = models.BooleanField(
        "Конфигурация по умолчанию",
        default=False
    )

    created_at = models.DateTimeField(
        "Дата создания",
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        "Дата обновления",
        auto_now=True
    )

    class Meta:
        ordering = ['name']
        verbose_name = "Конфигурация контейнера"
        verbose_name_plural = "Конфигурации контейнеров"

    def __str__(self):
        return f"{self.name} ({self.length}×{self.width}×{self.height})"

    def calculate_base_price(self):
        """Расчет базовой цены"""
        # Упрощенный расчет
        height_m = int(self.height) / 1000
        length_m = int(self.length) / 1000
        width_m = int(self.width) / 1000
        volume = height_m * length_m * width_m

        base = volume * 50000  # 50 000 руб за м³

        # Модификаторы
        if self.container_type == 'sandwich':
            base *= 1.2
        if self.fire_resistance == 'II':
            base *= 1.3
        elif self.fire_resistance == 'III':
            base *= 1.15
        if self.operational_type == 'mobile':
            base *= 1.5

        return round(base, 2)

    def save(self, *args, **kwargs):
        if not self.base_price or self.base_price == 0:
            self.base_price = self.calculate_base_price()
        super().save(*args, **kwargs)

    @property
    def dimensions(self):
        return f"{self.length}×{self.width}×{self.height} мм"

    @property
    def volume(self):
        height_m = int(self.height) / 1000
        length_m = int(self.length) / 1000
        width_m = int(self.width) / 1000
        return round(height_m * length_m * width_m, 2)
