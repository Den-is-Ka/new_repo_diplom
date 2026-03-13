from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from catalog import models as catalog_models
from catalog.constants import CATALOG_TZ


def _has_field(model, field_name: str) -> bool:
    return any(f.name == field_name for f in model._meta.fields)


def _pick_field(model, candidates: list[str]) -> str | None:
    for c in candidates:
        if _has_field(model, c):
            return c
    return None


def _set_if_exists(obj, **kwargs):
    for k, v in kwargs.items():
        if _has_field(obj.__class__, k):
            setattr(obj, k, v)


class Command(BaseCommand):
    help = "Seed catalog data from technical specification constants."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Do not save changes to DB (everything will be rolled back).",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing catalog data before seeding.",
        )

    def _clear_catalog(self):
        """
        Чистим в безопасном порядке (зависимости):
        - EquipmentModule зависит от EquipmentCategory
        - EngineeringSystemOption зависит от EngineeringSystemGroup
        """
        catalog_models.EquipmentModule.objects.all().delete()
        catalog_models.EquipmentCategory.objects.all().delete()
        catalog_models.EngineeringSystemOption.objects.all().delete()
        catalog_models.EngineeringSystemGroup.objects.all().delete()

    @transaction.atomic
    def handle(self, *args, **options):
        dry_run: bool = bool(options.get("dry_run"))
        clear: bool = bool(options.get("clear"))

        EquipmentCategory = catalog_models.EquipmentCategory
        EquipmentModule = catalog_models.EquipmentModule
        EngineeringSystemGroup = catalog_models.EngineeringSystemGroup
        EngineeringSystemOption = catalog_models.EngineeringSystemOption

        # Поля на всякий случай “плавающие” (если модель менялась)
        category_name_field = _pick_field(EquipmentCategory, ["name", "title"])
        module_name_field = _pick_field(EquipmentModule, ["name", "title"])
        group_name_field = _pick_field(EngineeringSystemGroup, ["name", "title"])
        option_name_field = _pick_field(EngineeringSystemOption, ["name", "title"])

        if (
            not category_name_field
            or not module_name_field
            or not group_name_field
            or not option_name_field
        ):
            raise CommandError(
                "Не смог определить поля name/title в моделях. "
                "Проверьте модели EquipmentCategory/EquipmentModule/EngineeringSystemGroup/EngineeringSystemOption."
            )

        # Флаг “мультивыбора” у группы может называться по-разному
        group_multi_field = _pick_field(
            EngineeringSystemGroup,
            [
                "is_multi",
                "is_multiple",
                "multiple",
                "allow_multiple",
                "multi_select",
                "is_multiselect",
            ],
        )

        if clear:
            self.stdout.write(self.style.WARNING("Clearing existing catalog data..."))
            self._clear_catalog()

        self.stdout.write(
            self.style.MIGRATE_HEADING("Seeding equipment categories/modules...")
        )

        # Ожидаем формат:
        # CATALOG_TZ["equipment"] = { "<категория/тип>": ["<модуль1>", "<модуль2>", ...], ... }
        equipment_block = CATALOG_TZ.get("equipment")
        if not isinstance(equipment_block, dict):
            raise CommandError(
                "CATALOG_TZ['equipment'] должен быть dict вида {category_name: [module_names...] }"
            )

        for category_name, modules in equipment_block.items():
            if not isinstance(modules, (list, tuple)):
                raise CommandError(
                    f"CATALOG_TZ['equipment']['{category_name}'] должен быть списком модулей"
                )

            # Создаём категорию
            category, _ = EquipmentCategory.objects.get_or_create(
                **{category_name_field: category_name}
            )

            # Если в EquipmentCategory есть поле equipment_type — удобно продублировать туда имя “типа”
            # (у тебя оно есть, и это ок)
            _set_if_exists(category, equipment_type=category_name, is_active=True)

            # Полезно иметь code (если поле есть) — делаем простой slug-like код
            if _has_field(EquipmentCategory, "code") and not getattr(
                category, "code", None
            ):
                code = (
                    str(category_name)
                    .strip()
                    .lower()
                    .replace(" ", "_")
                    .replace("-", "_")
                )
                setattr(category, "code", code[:50])

            category.save()

            # Создаём модули, привязанные к категории
            for module_name in modules:
                lookup = {
                    module_name_field: module_name,
                    "category": category,  # <-- ВАЖНО: FK называется category
                }
                mod, _ = EquipmentModule.objects.get_or_create(**lookup)

                # Заполним безопасно, если поля есть
                _set_if_exists(mod, price=0, is_active=True)
                mod.save()

        self.stdout.write(
            self.style.MIGRATE_HEADING("Seeding engineering groups/options...")
        )

        engineering_block = CATALOG_TZ.get("engineering_groups")
        if not isinstance(engineering_block, dict):
            raise CommandError(
                "CATALOG_TZ['engineering_groups'] должен быть dict вида {group_name: {multi:bool, options:[...]}}"
            )

        for group_name, meta in engineering_block.items():
            group, _ = EngineeringSystemGroup.objects.get_or_create(
                **{group_name_field: group_name}
            )

            if group_multi_field:
                setattr(group, group_multi_field, bool(meta.get("multi", False)))
                group.save()

            options_list = meta.get("options", [])
            if not isinstance(options_list, (list, tuple)):
                raise CommandError(
                    f"engineering_groups['{group_name}']['options'] должен быть списком"
                )

            for opt_name in options_list:
                EngineeringSystemOption.objects.get_or_create(
                    **{option_name_field: opt_name, "group": group}
                )

        if dry_run:
            # откатываем всю транзакцию
            raise CommandError("DRY-RUN: changes rolled back (this is expected).")

        self.stdout.write(self.style.SUCCESS("✅ seed_catalog completed"))
