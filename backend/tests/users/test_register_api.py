import pytest
from django.contrib.auth import get_user_model

pytestmark = pytest.mark.django_db

User = get_user_model()


def test_register_success_and_token(api_client):
    payload = {
        "username": "new_user_1",
        "password": "StrongPass123",
        "email": "new_user_1@example.com",
        "company_name": "ООО Тест",
    }
    r = api_client.post("/api/users/register/", data=payload, format="json")
    assert r.status_code in (200, 201), r.content

    assert User.objects.filter(username="new_user_1").exists()
    u = User.objects.get(username="new_user_1")
    assert u.is_active is True

    # token obtain
    username_field = User.USERNAME_FIELD
    token_payload = {
        username_field: getattr(u, username_field),
        "password": "StrongPass123",
    }
    r = api_client.post("/api/token/", data=token_payload, format="json")
    assert r.status_code == 200, r.content
    t = r.json()
    assert "access" in t and "refresh" in t


def test_register_duplicate_username_returns_400_or_409(api_client):
    # existing user
    User.objects.create_user(
        username="dup_user",
        password="pass123",
        email="dup@example.com",
        company_name="ООО Dup",
    )

    r = api_client.post(
        "/api/users/register/",
        data={
            "username": "dup_user",
            "password": "pass123",
            "email": "dup2@example.com",
            "company_name": "ООО Dup2",
        },
        format="json",
    )
    # в зависимости от реализации может быть 400 или 409
    assert r.status_code in (400, 409), r.content


def test_register_empty_company_name_is_auto_filled(api_client):
    """
    По текущей реализации у тебя регистрация НЕ падает на company_name="",
    а создаёт пользователя (иначе User.save() бы бросил ValueError).
    Поэтому тест проверяет, что company_name в итоге НЕ пустой.
    """
    r = api_client.post(
        "/api/users/register/",
        data={
            "username": "u_no_company",
            "password": "qwer-1234",
            "email": "a@a.ru",
            "company_name": "",
        },
        format="json",
    )
    assert r.status_code in (200, 201), r.content

    u = User.objects.get(username="u_no_company")
    assert isinstance(u.company_name, str)
    assert u.company_name.strip() != ""
