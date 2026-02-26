import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()


@pytest.mark.django_db
def test_register_success_and_token():
    api = APIClient()

    payload = {
        "username": "new_user_1",
        "password": "StrongPass123",
        "email": "new_user_1@example.com",
        "company_name": "ООО Тест",
    }
    r = api.post("/api/users/register/", data=payload, format="json")
    assert r.status_code == 201

    assert User.objects.filter(username="new_user_1").exists()
    u = User.objects.get(username="new_user_1")
    assert u.is_active is True

    # token obtain
    username_field = User.USERNAME_FIELD
    token_payload = {username_field: getattr(u, username_field), "password": "StrongPass123"}
    r = api.post("/api/token/", data=token_payload, format="json")
    assert r.status_code == 200
    t = r.json()
    assert "access" in t and "refresh" in t


@pytest.mark.django_db
def test_register_duplicate_returns_400():
    api = APIClient()

    # ВАЖНО: company_name обязателен по User.save()
    User.objects.create_user(
        username="dup_user",
        password="pass123",
        email="dup@example.com",
        company_name="ООО Dup",
    )

    r = api.post("/api/users/register/", data={"username": "dup_user", "password": "pass123"}, format="json")
    assert r.status_code == 400
