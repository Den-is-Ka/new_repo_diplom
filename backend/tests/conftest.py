# backend/tests/conftest.py
import uuid

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from model_bakery import baker
from rest_framework.test import APIClient

User = get_user_model()


# --- Optional demo catalog (load inside test transaction, no side effects) ---
@pytest.fixture
def demo_catalog(db):
    """
    Loads demo catalog fixture inside the current test transaction.
    After test finishes, transaction rollbacks -> fixture data won't leak to other tests.
    Use this fixture only in tests that need catalog data.
    """
    call_command("loaddata", "fixtures/demo_catalog.json", verbosity=0)


# --- Users ---
@pytest.fixture
def customer(db):
    return User.objects.create_user(
        username="customer",
        password="pass12345",
        company_name="ООО Тест Клиент",
        email="customer@test.local",
        phone="+79990000001",
    )


@pytest.fixture
def manager(db):
    # ВАЖНО: НЕ передаем phone_confirmed, т.к. поля нет в модели -> падение.
    return User.objects.create_user(
        username="manager",
        password="pass12345",
        is_staff=True,
        company_name="ООО Тест Менеджер",
        email="manager@test.local",
        phone="+79990000002",
    )


# --- API clients ---
@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def auth_client(db, api_client):
    """
    Authenticated DRF client via JWT access token.
    """
    uname = f"t_client_{uuid.uuid4().hex[:8]}"
    User.objects.create_user(
        username=uname,
        password="client123",
        email=f"{uname}@example.com",
        company_name="Demo Company",
        phone="+79990000999",
    )

    r = api_client.post("/api/token/", {"username": uname, "password": "client123"}, format="json")
    assert r.status_code == 200, r.content
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")
    return api_client


# --- Staticfiles for template rendering in tests ---
@pytest.fixture(autouse=True)
def _disable_static_manifest_strict(settings):
    """
    В тестах мы не запускаем collectstatic, поэтому ManifestStaticFilesStorage
    может падать на static('ui/app.css'). Переключаемся на обычное хранилище.
    """
    storages = getattr(settings, "STORAGES", None) or {}
    default_storage = storages.get("default", {"BACKEND": "django.core.files.storage.FileSystemStorage"})
    settings.STORAGES = {
        "default": default_storage,
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }


# --- Catalog / Configurator factories ---
@pytest.fixture
def equipment_module(db):
    return baker.make("catalog.EquipmentModule", price=1000)


@pytest.fixture
def configuration(db, customer):
    return baker.make("configurator.Configuration", user=customer)


@pytest.fixture
def configuration_with_module(db, configuration, equipment_module):
    baker.make(
        "configurator.ConfigurationModule",
        configuration=configuration,
        module=equipment_module,
        quantity=1,
    )
    return configuration
