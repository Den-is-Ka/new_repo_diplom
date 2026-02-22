import pytest
from model_bakery import baker
from rest_framework.exceptions import ValidationError

from catalog.models import CompatibilityRule, EquipmentCategory, EquipmentModule
from configurator.services import validate_configuration_for_submit


def _add_module_to_configuration(cfg, module, quantity=1):
    """
    Универсально добавляем module_item в cfg, не зная названия промежуточной модели.
    Берём модель через cfg.module_items.model и находим FK-поля динамически.
    """
    item_model = cfg.module_items.model

    cfg_fk = None
    mod_fk = None

    for f in item_model._meta.fields:
        remote = getattr(f, "remote_field", None)
        if not remote:
            continue
        if remote.model == cfg.__class__:
            cfg_fk = f.name
        if remote.model == EquipmentModule:
            mod_fk = f.name

    assert cfg_fk is not None, "Не найден FK на Configuration в module_items.model"
    assert mod_fk is not None, "Не найден FK на EquipmentModule в module_items.model"

    kwargs = {cfg_fk: cfg, mod_fk: module}

    if any(f.name == "quantity" for f in item_model._meta.fields):
        kwargs["quantity"] = quantity

    item_model.objects.create(**kwargs)


@pytest.mark.django_db
def test_exclusion_rule_blocks_two_modules(configuration):
    cat = baker.make(EquipmentCategory, code="C1")
    m1 = baker.make(EquipmentModule, category=cat, name="M1")
    m2 = baker.make(EquipmentModule, category=cat, name="M2")

    _add_module_to_configuration(configuration, m1, 1)
    _add_module_to_configuration(configuration, m2, 1)

    rule = baker.make(
        CompatibilityRule,
        name="No together",
        rule_type=CompatibilityRule.RuleType.EXCLUSION,
        is_active=True,
    )
    rule.modules.add(m1, m2)

    with pytest.raises(ValidationError) as e:
        validate_configuration_for_submit(configuration)

    payload = e.value.detail
    assert any(str(d["code"]) == "INCOMPATIBLE_MODULES" for d in payload["details"])


@pytest.mark.django_db
def test_group_rule_blocks_two_modules(configuration):
    cat = baker.make(EquipmentCategory, code="C2")
    m1 = baker.make(EquipmentModule, category=cat, name="G1")
    m2 = baker.make(EquipmentModule, category=cat, name="G2")

    _add_module_to_configuration(configuration, m1, 1)
    _add_module_to_configuration(configuration, m2, 1)

    rule = baker.make(
        CompatibilityRule,
        name="Only one in group",
        rule_type=CompatibilityRule.RuleType.GROUP,
        is_active=True,
    )
    rule.modules.add(m1, m2)

    with pytest.raises(ValidationError) as e:
        validate_configuration_for_submit(configuration)

    payload = e.value.detail
    assert any(str(d["code"]) == "INCOMPATIBLE_MODULES" for d in payload["details"])


@pytest.mark.django_db
def test_requirement_rule_requires_module(configuration):
    cat = baker.make(EquipmentCategory, code="C3")
    trigger = baker.make(EquipmentModule, category=cat, name="Trigger")
    required = baker.make(EquipmentModule, category=cat, name="Required")

    _add_module_to_configuration(configuration, trigger, 1)

    rule = baker.make(
        CompatibilityRule,
        name="Need Required",
        rule_type=CompatibilityRule.RuleType.REQUIREMENT,
        required_module=required,
        is_active=True,
    )
    rule.modules.add(trigger)

    with pytest.raises(ValidationError) as e:
        validate_configuration_for_submit(configuration)

    payload = e.value.detail
    assert any(str(d["code"]) == "MISSING_REQUIRED_MODULE" for d in payload["details"])


@pytest.mark.django_db
def test_limit_rule_blocks_exceed(configuration):
    cat = baker.make(EquipmentCategory, code="C4")
    m1 = baker.make(EquipmentModule, category=cat, name="A")
    m2 = baker.make(EquipmentModule, category=cat, name="B")

    _add_module_to_configuration(configuration, m1, 2)
    _add_module_to_configuration(configuration, m2, 2)  # total 4

    rule = baker.make(
        CompatibilityRule,
        name="Max 3",
        rule_type=CompatibilityRule.RuleType.LIMIT,
        max_quantity=3,
        is_active=True,
    )
    rule.modules.add(m1, m2)

    with pytest.raises(ValidationError) as e:
        validate_configuration_for_submit(configuration)

    payload = e.value.detail
    assert any(str(d["code"]) == "MODULE_LIMIT_EXCEEDED" for d in payload["details"])


@pytest.mark.django_db
def test_category_exclusion_blocks_excluded_categories(configuration):
    cat_main = baker.make(EquipmentCategory, code="MAIN")
    cat_bad = baker.make(EquipmentCategory, code="BAD")
    cat_ok = baker.make(EquipmentCategory, code="OK")

    m_main = baker.make(EquipmentModule, category=cat_main, name="Main")
    m_bad = baker.make(EquipmentModule, category=cat_bad, name="Bad")
    m_ok = baker.make(EquipmentModule, category=cat_ok, name="Ok")

    _add_module_to_configuration(configuration, m_main, 1)
    _add_module_to_configuration(configuration, m_bad, 1)
    _add_module_to_configuration(configuration, m_ok, 1)

    rule = baker.make(
        CompatibilityRule,
        name="Main excludes Bad category",
        rule_type=CompatibilityRule.RuleType.CATEGORY_EXCLUSION,
        category=cat_main,
        is_active=True,
    )
    rule.excluded_categories.add(cat_bad)

    with pytest.raises(ValidationError) as e:
        validate_configuration_for_submit(configuration)

    payload = e.value.detail
    assert any(str(d["code"]) == "EXCLUDED_CATEGORY_SELECTED" for d in payload["details"])
