from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Set

from django.conf import settings
from rest_framework.exceptions import ValidationError

from catalog.models import CompatibilityRule, EquipmentModule
from configurator.models import Configuration


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    field: Optional[str] = None


def _as_drf_error(issues: List[ValidationIssue]) -> ValidationError:
    """
    Стабильный формат ошибки для API/UI:
    {
      "code": "CONFIG_INVALID",
      "details": [{"code": "...", "field": "...", "message": "..."}, ...]
    }
    """
    return ValidationError(
        {
            "code": "CONFIG_INVALID",
            "details": [
                {"code": i.code, "field": i.field, "message": i.message} for i in issues
            ],
        }
    )


def _get_required_module_codes() -> Set[str]:
    return {
        str(x).strip()
        for x in getattr(settings, "CONFIG_REQUIRED_MODULE_CODES", [])
        if str(x).strip()
    }


def _get_required_category_codes() -> Set[str]:
    return {
        str(x).strip()
        for x in getattr(settings, "CONFIG_REQUIRED_CATEGORY_CODES", [])
        if str(x).strip()
    }


def _module_names_by_ids(ids: Set[int]) -> List[str]:
    """Имя модулей по id (для человекочитаемых ошибок)."""
    if not ids:
        return []
    qs = EquipmentModule.objects.filter(id__in=list(ids)).values_list("name", flat=True)
    return sorted({str(x) for x in qs if x})


def _category_codes_by_ids(ids: Set[int]) -> List[str]:
    """Коды категорий по id (для человекочитаемых ошибок)."""
    from catalog.models import EquipmentCategory  # локальный импорт, чтобы избежать циклов

    if not ids:
        return []
    qs = EquipmentCategory.objects.filter(id__in=list(ids)).values_list("code", flat=True)
    return sorted({str(x) for x in qs if x})


def _validate_required_blocks(cfg: Configuration, issues: List[ValidationIssue]) -> None:
    """
    Required blocks:
      - по коду модуля (EquipmentModule.code если есть)
      - по коду категории (EquipmentCategory.code)
    Управляется через settings:
      CONFIG_REQUIRED_MODULE_CODES
      CONFIG_REQUIRED_CATEGORY_CODES
    """
    required_module_codes = _get_required_module_codes()
    required_category_codes = _get_required_category_codes()

    if not required_module_codes and not required_category_codes:
        return  # правило выключено

    module_items = cfg.module_items.select_related("module", "module__category").all()

    selected_module_codes: Set[str] = set()
    selected_category_codes: Set[str] = set()

    for item in module_items:
        m = item.module

        m_code = getattr(m, "code", None)
        if m_code:
            selected_module_codes.add(str(m_code))

        cat = getattr(m, "category", None)
        cat_code = getattr(cat, "code", None) if cat is not None else None
        if cat_code:
            selected_category_codes.add(str(cat_code))

    missing_modules = sorted(required_module_codes - selected_module_codes)
    missing_categories = sorted(required_category_codes - selected_category_codes)

    if missing_modules or missing_categories:
        parts = []
        if missing_modules:
            parts.append(f"модули: {', '.join(missing_modules)}")
        if missing_categories:
            parts.append(f"категории: {', '.join(missing_categories)}")

        issues.append(
            ValidationIssue(
                code="MISSING_REQUIRED_BLOCKS",
                field="modules",
                message="Отсутствуют обязательные блоки (" + "; ".join(parts) + ").",
            )
        )


def _validate_compatibility_rules(cfg: Configuration, issues: List[ValidationIssue]) -> None:
    """
    Реальная проверка CompatibilityRule из catalog.models

    Интерпретация (MVP, но архитектурно убедительная):
      - EXCLUSION / GROUP: нельзя иметь одновременно 2+ модулей из rule.modules
      - REQUIREMENT: если выбран любой модуль из rule.modules ИЛИ выбрана rule.category,
                     то required_module должен быть выбран
      - LIMIT: суммарное quantity по rule.modules <= max_quantity
      - CATEGORY_EXCLUSION: если выбрана rule.category, то категории из excluded_categories запрещены
    """
    module_items = cfg.module_items.select_related("module", "module__category").all()

    selected_module_ids = {mi.module_id for mi in module_items}
    selected_category_ids = {
        mi.module.category_id
        for mi in module_items
        if getattr(mi.module, "category_id", None)
    }

    # суммарное quantity по module_id
    qty_by_module_id: Dict[int, int] = {}
    for mi in module_items:
        qty_by_module_id[mi.module_id] = qty_by_module_id.get(mi.module_id, 0) + int(
            getattr(mi, "quantity", 0) or 0
        )

    rules = (
        CompatibilityRule.objects.filter(is_active=True)
        .prefetch_related("modules", "excluded_categories")
        .select_related("required_module", "category")
    )

    for rule in rules:
        rtype = rule.rule_type

        rule_module_ids = set(rule.modules.values_list("id", flat=True))
        picked_in_rule = selected_module_ids.intersection(rule_module_ids)

        # EXCLUSION / GROUP: 2+ модуля из набора нельзя
        if rtype in (
            CompatibilityRule.RuleType.EXCLUSION,
            CompatibilityRule.RuleType.GROUP,
        ):
            if len(picked_in_rule) >= 2:
                names = _module_names_by_ids(set(picked_in_rule))
                pretty = ", ".join(names) if names else "несколько модулей"
                kind = "взаимоисключение" if rtype == CompatibilityRule.RuleType.EXCLUSION else "группа"
                issues.append(
                    ValidationIssue(
                        code="INCOMPATIBLE_MODULES",
                        field="modules",
                        message=f"Правило '{rule.name}' ({kind}): нельзя выбрать вместе: {pretty}.",
                    )
                )

        # REQUIREMENT: триггерится либо выбранными модулями, либо категорией
        if rtype == CompatibilityRule.RuleType.REQUIREMENT:
            required_id = rule.required_module_id
            if required_id:
                triggered_by_modules = len(picked_in_rule) >= 1
                triggered_by_category = bool(
                    rule.category_id and rule.category_id in selected_category_ids
                )

                if (triggered_by_modules or triggered_by_category) and (
                    required_id not in selected_module_ids
                ):
                    required_name = (
                        rule.required_module.name
                        if getattr(rule, "required_module", None) is not None
                        else "required module"
                    )
                    issues.append(
                        ValidationIssue(
                            code="MISSING_REQUIRED_MODULE",
                            field="modules",
                            message=f"Правило '{rule.name}': требуется модуль '{required_name}'.",
                        )
                    )

        # LIMIT: суммарная квота по rule.modules
        if rtype == CompatibilityRule.RuleType.LIMIT:
            if rule.max_quantity is not None and rule_module_ids:
                total_qty = sum(qty_by_module_id.get(mid, 0) for mid in rule_module_ids)
                if total_qty > rule.max_quantity:
                    names = _module_names_by_ids(set(rule_module_ids))
                    pretty = ", ".join(names) if names else "модули правила"
                    issues.append(
                        ValidationIssue(
                            code="MODULE_LIMIT_EXCEEDED",
                            field="modules",
                            message=(
                                f"Правило '{rule.name}' (лимит): превышено количество для [{pretty}] "
                                f"(max={rule.max_quantity}, сейчас={total_qty})."
                            ),
                        )
                    )

        # CATEGORY_EXCLUSION
        if rtype == CompatibilityRule.RuleType.CATEGORY_EXCLUSION:
            if rule.category_id and rule.category_id in selected_category_ids:
                excluded_ids = set(rule.excluded_categories.values_list("id", flat=True))
                bad = selected_category_ids.intersection(excluded_ids)
                if bad:
                    excluded_codes = _category_codes_by_ids(excluded_ids)
                    bad_codes = _category_codes_by_ids(bad)
                    exc_pretty = ", ".join(excluded_codes) if excluded_codes else "категории"
                    bad_pretty = ", ".join(bad_codes) if bad_codes else "категории"
                    cat_code = getattr(rule.category, "code", None) if getattr(rule, "category", None) else None

                    issues.append(
                        ValidationIssue(
                            code="EXCLUDED_CATEGORY_SELECTED",
                            field="modules",
                            message=(
                                f"Правило '{rule.name}' (исключение по категории): "
                                f"при выборе категории '{cat_code or rule.category_id}' запрещены категории [{exc_pretty}]. "
                                f"Сейчас выбрано из запрещённых: [{bad_pretty}]."
                            ),
                        )
                    )


def validate_configuration_for_submit(cfg: Configuration) -> None:
    """
    Строгая бизнес-валидация перед submit:
      - не пустая
      - quantity корректны
      - required blocks (через settings)
      - compatibility rules (через catalog.CompatibilityRule)
    """
    issues: List[ValidationIssue] = []

    module_items = cfg.module_items.select_related("module", "module__category").all()
    has_modules = module_items.exists()

    # engineering_items у тебя есть (используется в orders/services.py)
    eng_items = cfg.engineering_items.all()
    has_eng = eng_items.exists()

    # 1) не пустая
    if not has_modules and not has_eng:
        issues.append(
            ValidationIssue(
                code="EMPTY_CONFIGURATION",
                field=None,
                message="Нельзя отправить пустую конфигурацию: добавьте модули и/или инженерные системы.",
            )
        )

    # 2) quantity по модулям
    for item in module_items:
        qty = getattr(item, "quantity", 0)
        if qty <= 0:
            issues.append(
                ValidationIssue(
                    code="INVALID_QUANTITY",
                    field="modules",
                    message=f"Некорректное количество у модуля '{item.module.name}': {qty}. Должно быть > 0.",
                )
            )

    # 3) quantity по инженерным системам (если поле quantity есть)
    for item in eng_items:
        if hasattr(item, "quantity"):
            qty = getattr(item, "quantity", 1)
            if qty <= 0:
                es = getattr(item, "engineering_system", None)
                name = getattr(es, "name", None) if es is not None else None
                issues.append(
                    ValidationIssue(
                        code="INVALID_QUANTITY",
                        field="engineering_systems",
                        message=f"Некорректное количество у инженерной системы '{name or 'unknown'}': {qty}. Должно быть > 0.",
                    )
                )

    # 4) required blocks (settings)
    _validate_required_blocks(cfg, issues)

    # 5) compatibility rules (catalog)
    _validate_compatibility_rules(cfg, issues)

    if issues:
        raise _as_drf_error(issues)
