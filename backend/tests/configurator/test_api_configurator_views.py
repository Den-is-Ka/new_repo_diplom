from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from catalog.models import (
    EngineeringSystemGroup,
    EngineeringSystemOption,
    EquipmentCategory,
    EquipmentModule,
)
from configurator.models import Configuration

User = get_user_model()


@pytest.mark.django_db
def test_configurator_api_happy_path_and_lock():
    """
    Покрываем ключевые пути configurator/views.py:
    - main_categories / sub_categories / available_modules
    - create config
    - patch module_ids
    - set_engineering
    - validate
    - submit (created True/False)
    - lock после submit: PATCH и set_engineering -> 400
    - list: клиент видит только свои
    """
    api = APIClient()

    # ВАЖНО: company_name обязателен по User.save()
    u1 = User.objects.create_user(
        username="u1",
        password="pass123",
        email="u1@example.com",
        company_name="ООО Тест (u1)",
    )
    api.force_authenticate(user=u1)

    # --- catalog minimal tree for serializer/queryset filters ---
    # root -> main -> sub
    root = EquipmentCategory.objects.create(
        name="Оборудование",
        parent=None,
        equipment_type="root",
        description="root",
        order=0,
        is_active=True,
        code="ROOT",
    )
    main = EquipmentCategory.objects.create(
        name="ДГУ",
        parent=root,  # parent != null, parent.parent == null
        equipment_type="DGU",
        description="main",
        order=1,
        is_active=True,
        code="DGU",
    )
    sub = EquipmentCategory.objects.create(
        name="до 50 кВт",
        parent=main,  # parent != null, parent.parent != null
        equipment_type="DGU",
        description="sub",
        order=1,
        is_active=True,
        code="DGU-50",
    )

    # module tied to sub-category
    m1 = EquipmentModule.objects.create(
        name="ДГУ до 50 кВт",
        category=sub,
        physical_type=None,
        applicable_to="DGU",
        description="",
        price_type="fixed",
        price=Decimal("120000.00"),
        main_image="",
        specifications={},
        is_active=True,
        is_default=False,
    )

    # engineering option
    g1 = EngineeringSystemGroup.objects.create(
        key="vent",
        code="2.5",
        title="Вентиляция",
        selection_mode="multi",
        order=0,
        is_active=True,
    )
    o1 = EngineeringSystemOption.objects.create(
        group=g1,
        code="2.5.1",
        title="Основная вытяжная",
        applicability="BOTH",
        price_type="fixed",
        price=Decimal("1000.00"),
        order=0,
        is_active=True,
    )

    # --- main_categories ---
    r = api.get("/api/configurator/configurations/main_categories/")
    assert r.status_code == 200
    data = r.json()
    assert any(x["name"] == "ДГУ" for x in data)

    # --- sub_categories: missing param ---
    r = api.get("/api/configurator/configurations/sub_categories/")
    assert r.status_code == 400

    # --- sub_categories: invalid id ---
    r = api.get(
        "/api/configurator/configurations/sub_categories/?main_category_id=999999"
    )
    assert r.status_code == 404

    # --- sub_categories: ok ---
    r = api.get(
        f"/api/configurator/configurations/sub_categories/?main_category_id={main.id}"
    )
    assert r.status_code == 200
    data = r.json()
    assert any(x["id"] == sub.id for x in data)

    # --- available_modules: missing category_id ---
    r = api.get("/api/configurator/configurations/available_modules/")
    assert r.status_code == 400

    # --- available_modules: ok ---
    r = api.get(
        f"/api/configurator/configurations/available_modules/?category_id={sub.id}"
    )
    assert r.status_code == 200
    data = r.json()
    assert any(x["id"] == m1.id for x in data)

    # --- create configuration ---
    payload = {"main_category_id": main.id, "sub_category_id": sub.id}
    r = api.post("/api/configurator/configurations/", data=payload, format="json")
    assert r.status_code in (200, 201)
    cfg_id = r.json()["id"]

    # --- patch modules (module_ids) ---
    r = api.patch(
        f"/api/configurator/configurations/{cfg_id}/",
        data={"module_ids": [m1.id]},
        format="json",
    )
    assert r.status_code == 200

    # --- set engineering (draft only) ---
    r = api.post(
        f"/api/configurator/configurations/{cfg_id}/set_engineering/",
        data={"engineering_option_ids": [o1.id]},
        format="json",
    )
    assert r.status_code == 200
    cfg_after_eng = r.json()
    assert cfg_after_eng.get("engineering_option_ids") == [o1.id]

    # --- validate should be valid and total_price should include module + engineering ---
    r = api.get(f"/api/configurator/configurations/{cfg_id}/validate/")
    assert r.status_code == 200
    v = r.json()
    assert v["is_valid"] is True
    assert Decimal(v["total_price"]) == Decimal("121000.00")  # 120000 + 1000

    # --- submit (created True) ---
    r = api.post(
        f"/api/configurator/configurations/{cfg_id}/submit/", data={}, format="json"
    )
    assert r.status_code in (200, 201)
    s1 = r.json()
    assert s1["created"] is True
    assert "order_id" in s1

    # --- submit again (created False) ---
    r = api.post(
        f"/api/configurator/configurations/{cfg_id}/submit/", data={}, format="json"
    )
    assert r.status_code == 200
    s2 = r.json()
    assert s2["created"] is False

    # --- lock checks: PATCH after submit => 400+ ---
    r = api.patch(
        f"/api/configurator/configurations/{cfg_id}/",
        data={"description": "x"},
        format="json",
    )
    assert r.status_code >= 400

    # --- lock checks: set_engineering after submit => 400 ---
    r = api.post(
        f"/api/configurator/configurations/{cfg_id}/set_engineering/",
        data={"engineering_option_ids": [o1.id]},
        format="json",
    )
    assert r.status_code == 400

    # --- list filtering: other user's config should not be visible ---
    u2 = User.objects.create_user(
        username="u2",
        password="pass123",
        email="u2@example.com",
        company_name="ООО Тест (u2)",
    )
    Configuration.objects.create(
        user=u2,
        name="other",
        status=Configuration.Status.DRAFT,
        main_category=main,
        sub_category=sub,
        total_price=Decimal("0.00"),
    )

    r = api.get("/api/configurator/configurations/")
    assert r.status_code == 200
    rows = r.json()
    if isinstance(rows, dict) and "results" in rows:
        rows = rows["results"]
    assert all(x["user"]["username"] == "u1" for x in rows)
