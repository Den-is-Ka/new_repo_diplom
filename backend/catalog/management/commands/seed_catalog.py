from __future__ import annotations

import re

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Model
from django.utils.text import slugify

from catalog.constants import CATALOG_TZ
from catalog import models as catalog_models


# -----------------------------
# Engineering codes helpers
# -----------------------------

def _normalize_code(value: str | None) -> str:
    return (value or "").strip()


def _build_used_codes() -> set[str]:
    """
    Берём только НЕ пустые коды, иначе "" попадёт в set и всё ломает генерацию/проверки.
    """
    EngineeringSystemOption = getattr(catalog_models, "EngineeringSystemOption", None)
    if EngineeringSystemOption is None:
        return set()

    return set(
        EngineeringSystemOption.objects.exclude(code__isnull=True).exclude(code="").values_list("code", flat=True)
    )


def _group_prefix(group) -> str:
    """
    Подстраховка: если у группы нет поля code/оно пустое,
    используем key, иначе pk. Нужно для генерации уникальных option.code.
    """
    code = getattr(group, "code", None)
    if code:
        return str(code).strip()

    key = getattr(group, "key", None)
    if key:
        return str(key).strip()

    # pk уже есть, потому что группу мы сохраняем до опций
    return f"G{getattr(group, 'pk', '0')}"


def _next_option_code_for_group(group, used_codes: set[str]) -> str:
    """
    Генерирует следующий свободный код вида {group_prefix}.{n}
    Например: 2.1.1, 2.1.2 ...
    """
    prefix_base = _group_prefix(group)
    prefix = f"{prefix_base}."
    max_n = 0

    for code in used_codes:
        if not code.startswith(prefix):
            continue
        tail = code[len(prefix):]
        if tail.isdigit():
            max_n = max(max_n, int(tail))

    n = max_n + 1
    candidate = f"{prefix_base}.{n}"
    while candidate in used_codes:
        n += 1
        candidate = f"{prefix_base}.{n}"

    used_codes.add(candidate)
    return candidate


def _repair_blank_option_codes() -> int:
    """
    Чинит существующие записи с code='' или NULL.
    """
    EngineeringSystemOption = getattr(catalog_models, "EngineeringSystemOption", None)
    if EngineeringSystemOption is None:
        return 0

    used = _build_used_codes()
    qs = EngineeringSystemOption.objects.select_related("group").filter(code__in=["", None])
    if not qs.exists():
        return 0

    fixed = 0
    for opt in qs:
        opt.code = _next_option_code_for_group(opt.group, used)
        opt.save(update_fields=["code"])
        fixed += 1
    return fixed


_GROUP_CODE_RE = re.compile(r"^\s*(\d+\.\d+)\s*[\.\-–)]*\s*")


def _extract_group_code_and_title(raw: str) -> tuple[str | None, str]:
    """
    Пытаемся вытащить '2.1' из начала строки '2.1 Вентиляция', и вернуть (code, title).
    Если кода нет — вернём (None, исходная строка).
    """
    raw = (raw or "").strip()
    m = _GROUP_CODE_RE.match(raw)
    if not m:
        return None, raw
    code = m.group(1)
    title = raw[m.end():].strip() or raw
    return code, title


# -----------------------------
# Generic model helpers
# -----------------------------

def _has_field(model: type[Model], field_name: str) -> bool:
    return any(f.name == field_name for f in model._meta.fields)


def _pick_field(model: type[Model], candidates: list[str]) -> str | None:
    for c in candidates:
        if _has_field(model, c):
            return c
    return None


def _set_if_exists(obj: Model, **kwargs):
    for k, v in kwargs.items():
        if _has_field(obj.__class__, k):
            setattr(obj, k, v)


def _get_or_create_default_physical_type():
    """
    Создаём дефолтный EquipmentPhysicalType (если модель есть).
    Нужен, потому что EquipmentModule.physical_type у тебя в модели часто обязательный,
    а сид из ТЗ про physical_type ничего не знает.
    """
    EquipmentPhysicalType = getattr(catalog_models, "EquipmentPhysicalType", None)
    if EquipmentPhysicalType is None:
        return None

    pt_name_field = _pick_field(EquipmentPhysicalType, ["name", "title"])
    if not pt_name_field:
        return None

    defaults = {}
    if _has_field(EquipmentPhysicalType, "applicable_category"):
        defaults["applicable_category"] = "UNIVERSAL"
    if _has_field(EquipmentPhysicalType, "order"):
        defaults["order"] = 0
    if _has_field(EquipmentPhysicalType, "description"):
        defaults["description"] = ""

    obj, _ = EquipmentPhysicalType.objects.get_or_create(
        **{pt_name_field: "Общий"},
        defaults=defaults,
    )
    return obj


def _infer_equipment_type_from_category_name(name: str) -> str | None:
    if not name:
        return None
    n = name.strip().lower()
    if "дгу" in n:
        return "DGU"
    if "компресс" in n:
        return "COMPRESSOR"
    return "UNIVERSAL"


def _infer_applicable_to_from_category_name(name: str) -> str | None:
    if not name:
        return None
    n = name.strip().lower()
    if "дгу" in n:
        return "DGU"
    if "компресс" in n:
        return "COMPRESSOR"
    return "BOTH"


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

    @transaction.atomic
    def handle(self, *args, **options):
        dry_run: bool = bool(options.get("dry_run"))
        clear: bool = bool(options.get("clear"))

        EquipmentCategory = getattr(catalog_models, "EquipmentCategory", None)
        EquipmentModule = getattr(catalog_models, "EquipmentModule", None)
        EngineeringSystemGroup = getattr(catalog_models, "EngineeringSystemGroup", None)
        EngineeringSystemOption = getattr(catalog_models, "EngineeringSystemOption", None)

        missing = [
            name
            for name, obj in [
                ("EquipmentCategory", EquipmentCategory),
                ("EquipmentModule", EquipmentModule),
                ("EngineeringSystemGroup", EngineeringSystemGroup),
                ("EngineeringSystemOption", EngineeringSystemOption),
            ]
            if obj is None
        ]
        if missing:
            raise CommandError(f"Missing models in catalog.models: {', '.join(missing)}")

        # поля-имена
        category_name_field = _pick_field(EquipmentCategory, ["name", "title"])
        module_name_field = _pick_field(EquipmentModule, ["name", "title"])
        if not category_name_field:
            raise CommandError("EquipmentCategory must have a 'name' or 'title' field.")
        if not module_name_field:
            raise CommandError("EquipmentModule must have a 'name' or 'title' field.")

        # FK модуля на категорию
        module_category_fk = _pick_field(
            EquipmentModule,
            ["category", "equipment_category", "equipment_type", "type"],
        )

        # optional поля в модели модуля
        module_applicable_field = _pick_field(EquipmentModule, ["applicable_to"])
        module_physical_fk = _pick_field(EquipmentModule, ["physical_type", "physical"])
        module_dimensions_field = _pick_field(EquipmentModule, ["dimensions"])
        module_desc_field = _pick_field(EquipmentModule, ["description"])

        # category extra fields
        category_equipment_type_field = _pick_field(EquipmentCategory, ["equipment_type"])
        category_desc_field = _pick_field(EquipmentCategory, ["description"])
        category_order_field = _pick_field(EquipmentCategory, ["order"])
        category_is_active_field = _pick_field(EquipmentCategory, ["is_active"])

        # engineering fields
        group_multi_field = _pick_field(
            EngineeringSystemGroup,
            ["selection_mode", "is_multi", "is_multiple", "multiple", "allow_multiple", "multi_select", "is_multiselect"],
        )
        group_name_field = _pick_field(EngineeringSystemGroup, ["name", "title"])
        option_name_field = _pick_field(EngineeringSystemOption, ["name", "title"])
        if not group_name_field:
            raise CommandError("EngineeringSystemGroup must have a 'name' or 'title' field.")
        if not option_name_field:
            raise CommandError("EngineeringSystemOption must have a 'name' or 'title' field.")

        group_code_field = _pick_field(EngineeringSystemGroup, ["code"])
        group_key_field = _pick_field(EngineeringSystemGroup, ["key"])
        option_code_field = _pick_field(EngineeringSystemOption, ["code"])
        if not option_code_field:
            raise CommandError("EngineeringSystemOption must have a 'code' field (unique).")

        # дефолтный physical_type (если модель есть)
        default_pt = _get_or_create_default_physical_type()

        if clear:
            self.stdout.write(self.style.WARNING("⚠️ Clearing existing seeded data..."))
            EngineeringSystemOption.objects.all().delete()
            EngineeringSystemGroup.objects.all().delete()
            EquipmentModule.objects.all().delete()
            EquipmentCategory.objects.all().delete()

        # ----------------------------
        # 1) Equipment categories/modules
        # ----------------------------
        self.stdout.write(self.style.MIGRATE_HEADING("Seeding equipment categories/modules..."))
        equipment_map = CATALOG_TZ.get("equipment") or {}
        if not isinstance(equipment_map, dict):
            raise CommandError("CATALOG_TZ['equipment'] must be a dict: {category_name: [modules...] }")

        category_order_counter = 0

        for category_name, modules in equipment_map.items():
            if not category_name:
                continue

            category_defaults = {}
            if category_desc_field:
                category_defaults[category_desc_field] = ""
            if category_order_field:
                category_defaults[category_order_field] = category_order_counter
            if category_is_active_field:
                category_defaults[category_is_active_field] = True
            if category_equipment_type_field:
                category_defaults[category_equipment_type_field] = _infer_equipment_type_from_category_name(category_name)

            category, _ = EquipmentCategory.objects.get_or_create(
                **{category_name_field: category_name},
                defaults=category_defaults,
            )
            category_order_counter += 1

            if not isinstance(modules, (list, tuple)):
                raise CommandError(f"Modules for '{category_name}' must be a list/tuple.")

            for module_name in modules:
                if not module_name:
                    continue

                lookup = {module_name_field: module_name}
                if module_category_fk:
                    lookup[module_category_fk] = category

                module_defaults = {}
                if module_desc_field:
                    module_defaults[module_desc_field] = ""
                if module_applicable_field:
                    module_defaults[module_applicable_field] = _infer_applicable_to_from_category_name(category_name)
                if module_dimensions_field:
                    module_defaults[module_dimensions_field] = ""

                if default_pt is not None and module_physical_fk:
                    module_defaults[module_physical_fk] = default_pt

                mod, _created = EquipmentModule.objects.get_or_create(**lookup, defaults=module_defaults)

                if default_pt is not None and module_physical_fk and getattr(mod, f"{module_physical_fk}_id", None) is None:
                    setattr(mod, module_physical_fk, default_pt)

                _set_if_exists(mod, price=0, cost=0, base_price=0)
                mod.save()

        # ----------------------------
        # 2) Engineering groups/options (FIXED)
        # ----------------------------
        self.stdout.write(self.style.MIGRATE_HEADING("Seeding engineering groups/options..."))
        eng_map = CATALOG_TZ.get("engineering_groups") or {}
        if not isinstance(eng_map, dict):
            raise CommandError("CATALOG_TZ['engineering_groups'] must be a dict: {group_name: {multi, options}}")

        # 2.1 Создаём/обновляем группы так, чтобы у них был нормальный code (если поле есть)
        groups_by_title: dict[str, Model] = {}
        auto_group_index = 1  # если в названии нет "2.1"

        for raw_group_name, meta in eng_map.items():
            if not raw_group_name:
                continue
            if not isinstance(meta, dict):
                raise CommandError(f"engineering_groups['{raw_group_name}'] must be dict.")

            parsed_code, clean_title = _extract_group_code_and_title(raw_group_name)
            meta_code = _normalize_code(meta.get("code"))
            group_code = meta_code or parsed_code or f"2.{auto_group_index}"
            auto_group_index += 1

            meta_key = _normalize_code(meta.get("key"))
            group_key = meta_key or f"grp_{group_code.replace('.', '_')}"
            if group_key_field and len(group_key) > 64:
                group_key = slugify(clean_title, allow_unicode=True)[:64] or group_key[:64]

            is_multi = bool(meta.get("multi", False))

            # пытаемся найти по code (если есть), иначе по title
            group = None
            if group_code_field:
                group = EngineeringSystemGroup.objects.filter(**{group_code_field: group_code}).first()

            if group is None:
                group, _ = EngineeringSystemGroup.objects.get_or_create(**{group_name_field: clean_title})

            update_fields: list[str] = []

            if group_code_field and not getattr(group, group_code_field, None):
                setattr(group, group_code_field, group_code)
                update_fields.append(group_code_field)

            if group_key_field and not getattr(group, group_key_field, None):
                setattr(group, group_key_field, group_key)
                update_fields.append(group_key_field)

            if group_multi_field:
                if group_multi_field == "selection_mode":
                    new_val = "multi" if is_multi else "single"
                    if getattr(group, "selection_mode", None) != new_val:
                        setattr(group, "selection_mode", new_val)
                        update_fields.append("selection_mode")
                else:
                    if getattr(group, group_multi_field, None) != is_multi:
                        setattr(group, group_multi_field, is_multi)
                        update_fields.append(group_multi_field)

            if update_fields:
                group.save(update_fields=update_fields)

            groups_by_title[clean_title] = group

        # 2.2 Чиним уже существующие опции с code='' / NULL (после того как у групп уже нормальные prefix)
        fixed = _repair_blank_option_codes()
        if fixed:
            self.stdout.write(self.style.WARNING(f"Fixed blank EngineeringSystemOption.code: {fixed}"))

        used_codes = _build_used_codes()

        # 2.3 Сидим опции: если кода нет — генерим {group_prefix}.1/{group_prefix}.2...
        for raw_group_name, meta in eng_map.items():
            if not raw_group_name:
                continue
            if not isinstance(meta, dict):
                continue

            _parsed_code, clean_title = _extract_group_code_and_title(raw_group_name)
            group = groups_by_title.get(clean_title)
            if group is None:
                continue

            options_list = meta.get("options") or []
            if not isinstance(options_list, (list, tuple)):
                raise CommandError(f"engineering_groups['{raw_group_name}']['options'] must be list/tuple.")

            for opt in options_list:
                # ✅ ВАЖНО: тут всегда инициализируем переменные
                if isinstance(opt, dict):
                    opt_name = (opt.get("title") or opt.get("name") or "").strip()
                    opt_code = _normalize_code(opt.get("code"))
                    opt_applicability = opt.get("applicability")
                    opt_price_type = opt.get("price_type")
                else:
                    opt_name = str(opt or "").strip()
                    opt_code = ""  # <--- фикс: раньше тут было обращение к opt_code, которого нет
                    opt_applicability = None
                    opt_price_type = None

                if not opt_name:
                    continue

                existing = EngineeringSystemOption.objects.filter(group=group, **{option_name_field: opt_name}).first()
                if existing:
                    cur_code = getattr(existing, option_code_field, None)
                    if cur_code in ("", None):
                        new_code = _next_option_code_for_group(group, used_codes)
                        setattr(existing, option_code_field, new_code)
                        existing.save(update_fields=[option_code_field])

                    if opt_applicability is not None and _has_field(EngineeringSystemOption, "applicability"):
                        existing.applicability = opt_applicability
                        existing.save(update_fields=["applicability"])
                    if opt_price_type is not None and _has_field(EngineeringSystemOption, "price_type"):
                        existing.price_type = opt_price_type
                        existing.save(update_fields=["price_type"])
                    continue

                # новая опция → обязательно задаём code (не пустой)
                opt_code = (opt_code or "").strip()
                if not opt_code or opt_code in used_codes:
                    opt_code = _next_option_code_for_group(group, used_codes)
                else:
                    used_codes.add(opt_code)

                create_kwargs = {
                    "group": group,
                    option_name_field: opt_name,
                    option_code_field: opt_code,
                }

                obj = EngineeringSystemOption.objects.create(**create_kwargs)

                if opt_applicability is not None:
                    _set_if_exists(obj, applicability=opt_applicability)
                if opt_price_type is not None:
                    _set_if_exists(obj, price_type=opt_price_type)
                if opt_applicability is not None or opt_price_type is not None:
                    obj.save()

        if dry_run:
            self.stdout.write(self.style.WARNING("🟡 DRY-RUN: rolling back transaction (no changes saved)."))
            transaction.set_rollback(True)
            return

        self.stdout.write(self.style.SUCCESS("✅ seed_catalog completed"))
