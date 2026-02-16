from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Set

from catalog.models import CompatibilityRule
from configurator.models import Configuration


def _is_descendant(category, ancestor) -> bool:
    """True если category == ancestor или category потомок ancestor по parent-ссылкам."""
    if not category or not ancestor:
        return False
    cur = category
    while cur:
        if cur.id == ancestor.id:
            return True
        cur = getattr(cur, "parent", None)
    return False


@dataclass
class ValidationResult:
    ok: bool
    issues: List[dict]


def validate_configuration(cfg: Configuration) -> ValidationResult:
    """
    Проверяет конфигурацию по активным CompatibilityRule.
    issues:
      { level: "error"|"warning", code: "...", message: "...", rule_id: int, rule_name: str }
    """
    issues: List[dict] = []

    # выбранные модули: id -> qty
    selected: Dict[int, int] = {}
    items = cfg.module_items.select_related("module", "module__category").all()
    for item in items:
        selected[item.module_id] = selected.get(item.module_id, 0) + int(item.quantity or 0)

    selected_ids: Set[int] = set(selected.keys())

    rules = (
        CompatibilityRule.objects.filter(is_active=True)
        .select_related("category", "required_module")
        .prefetch_related("modules", "excluded_categories")
    )

    for rule in rules:
        rtype = rule.rule_type
        rule_modules = list(rule.modules.all())
        rule_module_ids = {m.id for m in rule_modules}

        def add(level: str, code: str, message: str):
            issues.append(
                {
                    "level": level,
                    "code": code,
                    "message": message,
                    "rule_id": rule.id,
                    "rule_name": rule.name,
                }
            )

        # 1) EXCLUSION: любые 2+ модуля из rule.modules одновременно
        if rtype == CompatibilityRule.RuleType.EXCLUSION:
            chosen = [m for m in rule_modules if m.id in selected_ids]
            if len(chosen) >= 2:
                names = ", ".join(m.name for m in chosen)
                add("error", "EXCLUSION", f"Взаимоисключающие модули выбраны вместе: {names}")

        # 2) REQUIREMENT: если выбран любой из rule.modules -> требуется required_module
        elif rtype == CompatibilityRule.RuleType.REQUIREMENT:
            if not rule.required_module_id:
                continue
            trigger_selected = bool(rule_module_ids & selected_ids)
            if trigger_selected and (rule.required_module_id not in selected_ids):
                add("error", "REQUIREMENT", f"Требуется модуль: {rule.required_module.name}")

        # 3) GROUP: не более 1 модуля из группы
        elif rtype == CompatibilityRule.RuleType.GROUP:
            chosen = [m for m in rule_modules if m.id in selected_ids]
            if len(chosen) > 1:
                names = ", ".join(m.name for m in chosen)
                add("error", "GROUP_TOO_MANY", f"Из группы можно выбрать только один модуль. Сейчас: {names}")

        # 4) LIMIT: суммарное количество модулей из rule.modules <= max_quantity
        elif rtype == CompatibilityRule.RuleType.LIMIT:
            if not rule.max_quantity:
                continue
            total_qty = sum(selected.get(mid, 0) for mid in rule_module_ids)
            if total_qty > rule.max_quantity:
                add("error", "LIMIT", f"Превышен лимит '{rule.name}': {total_qty} > {rule.max_quantity}")

        # 5) CATEGORY_EXCLUSION:
        # если cfg.sub_category внутри rule.category -> запрещаем модули из excluded_categories (и их потомков)
        elif rtype == CompatibilityRule.RuleType.CATEGORY_EXCLUSION:
            if not rule.category_id or not cfg.sub_category_id:
                continue
            if not _is_descendant(cfg.sub_category, rule.category):
                continue

            excluded_cats = list(rule.excluded_categories.all())
            if not excluded_cats:
                continue

            bad = []
            for item in items:
                mod_cat = getattr(item.module, "category", None)
                if not mod_cat:
                    continue
                if any(_is_descendant(mod_cat, ex) for ex in excluded_cats):
                    bad.append(item.module.name)

            if bad:
                add("error", "CATEGORY_EXCLUSION", "Запрещённые модули по категории: " + ", ".join(sorted(set(bad))))

    ok = not any(i["level"] == "error" for i in issues)
    return ValidationResult(ok=ok, issues=issues)
