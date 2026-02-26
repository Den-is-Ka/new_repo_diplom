import pytest

pytestmark = pytest.mark.django_db

def _as_list(data):
    return data.get("results", data)

def test_catalog_equipment_categories(auth_client):
    r = auth_client.get("/api/catalog/equipment-categories/")
    assert r.status_code == 200
    items = _as_list(r.json())
    assert isinstance(items, list)
    assert len(items) >= 0

def test_catalog_engineering_options(auth_client):
    r = auth_client.get("/api/catalog/engineering-system-options/")
    assert r.status_code == 200
    items = _as_list(r.json())
    assert isinstance(items, list)
    assert len(items) >= 0

import pytest

pytestmark = pytest.mark.django_db

def _as_list(data):
    return data.get("results", data)

def test_catalog_equipment_categories(auth_client, demo_catalog):
    r = auth_client.get("/api/catalog/equipment-categories/")
    assert r.status_code == 200
    items = _as_list(r.json())
    assert isinstance(items, list)
    assert len(items) > 0

def test_catalog_engineering_options(auth_client, demo_catalog):
    r = auth_client.get("/api/catalog/engineering-system-options/")
    assert r.status_code == 200
    items = _as_list(r.json())
    assert isinstance(items, list)
    assert len(items) > 0
