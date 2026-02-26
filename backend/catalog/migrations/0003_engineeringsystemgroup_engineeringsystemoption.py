import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0002_containerconfiguration"),
    ]

    operations = [
        migrations.CreateModel(
            name="EngineeringSystemGroup",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "key",
                    models.CharField(
                        choices=[
                            ("power_reliability", "2.1 Надёжность энергоснабжения"),
                            ("climate", "2.2 Климатическое исполнение"),
                            ("lighting", "2.3 Освещение"),
                            ("heating", "2.4 Отопление"),
                            ("ventilation", "2.5 Вентиляция"),
                            ("microclimate_control", "2.6 Управление микроклиматом"),
                            ("fire_alarm", "2.7 Пожарная сигнализация"),
                            ("fire_suppression", "2.8 Пожаротушение"),
                            ("decision_point", "2.9 Место принятия решения"),
                        ],
                        max_length=64,
                        unique=True,
                        verbose_name="Ключ (для кода)",
                    ),
                ),
                (
                    "code",
                    models.CharField(
                        max_length=10, unique=True, verbose_name="Код по ТЗ"
                    ),
                ),
                ("title", models.CharField(max_length=255, verbose_name="Название")),
                (
                    "selection_mode",
                    models.CharField(
                        choices=[
                            ("single", "Один вариант"),
                            ("multi", "Несколько вариантов"),
                        ],
                        default="single",
                        max_length=8,
                        verbose_name="Режим выбора",
                    ),
                ),
                (
                    "order",
                    models.PositiveIntegerField(
                        default=0, verbose_name="Порядок отображения"
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(default=True, verbose_name="Активно"),
                ),
            ],
            options={
                "verbose_name": "Инженерные системы — группа",
                "verbose_name_plural": "Инженерные системы — группы",
                "ordering": ["order", "code"],
                "indexes": [
                    models.Index(
                        fields=["is_active", "order"],
                        name="catalog_eng_is_acti_8f43ea_idx",
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="EngineeringSystemOption",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "code",
                    models.CharField(
                        max_length=16, unique=True, verbose_name="Код по ТЗ"
                    ),
                ),
                ("title", models.CharField(max_length=255, verbose_name="Название")),
                (
                    "applicability",
                    models.CharField(
                        choices=[
                            ("BOTH", "ДГУ и Компрессор"),
                            ("DGU", "Только ДГУ"),
                            ("COMPRESSOR", "Только Компрессор"),
                        ],
                        default="BOTH",
                        max_length=20,
                        verbose_name="Применимость",
                    ),
                ),
                (
                    "price_type",
                    models.CharField(
                        choices=[
                            ("fixed", "Фиксированная цена"),
                            ("individual", "Индивидуальный расчёт"),
                            ("request", "По запросу"),
                        ],
                        default="fixed",
                        max_length=20,
                        verbose_name="Тип цены",
                    ),
                ),
                (
                    "price",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        help_text="Заполняется только если price_type='fixed'",
                        max_digits=12,
                        null=True,
                        validators=[django.core.validators.MinValueValidator(0)],
                        verbose_name="Цена, руб.",
                    ),
                ),
                (
                    "order",
                    models.PositiveIntegerField(
                        default=0, verbose_name="Порядок отображения"
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(default=True, verbose_name="Активно"),
                ),
                (
                    "group",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="options",
                        to="catalog.engineeringsystemgroup",
                        verbose_name="Группа",
                    ),
                ),
            ],
            options={
                "verbose_name": "Инженерные системы — опция",
                "verbose_name_plural": "Инженерные системы — опции",
                "ordering": ["group__order", "group__code", "order", "code"],
                "indexes": [
                    models.Index(
                        fields=["group", "is_active"],
                        name="catalog_eng_group_i_8e8192_idx",
                    ),
                    models.Index(fields=["code"], name="catalog_eng_code_9df208_idx"),
                ],
            },
        ),
    ]
