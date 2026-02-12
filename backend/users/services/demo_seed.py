from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db import transaction


def _out(stdout, message: str) -> None:
    """Пишем либо в stdout (management command), либо в консоль."""
    if stdout is not None:
        stdout.write(message)
    else:
        print(message)


@transaction.atomic
def seed_demo_users(stdout=None) -> int:
    """
    Создаёт/обновляет демо-пользователей.
    Можно запускать много раз — не будет падать из-за дублей.
    Возвращает количество НОВЫХ созданных пользователей.
    """
    User = get_user_model()

    # Список демо-пользователей по ТЗ (поправил битые/обрезанные строки на нормальные)
    demo_users = [
        {
            "username": "client_dgu",
            "email": "dgu_client@industrial.com",
            "password": "client123",
            "company_name": "Промышленные решения",
            "phone": "+79161234567",
            "first_name": "Алексей",
            "last_name": "Иванов",
        },
        {
            "username": "client_compressor",
            "email": "compressor_client@factory.ru",
            "password": "client123",
            "company_name": 'Завод "Металлург"',
            "phone": "+79031234567",
            "first_name": "Мария",
            "last_name": "Петрова",
        },
        {
            "username": "manager1",
            "email": "manager@container-company.com",
            "password": "manager123",
            "company_name": "КонтейнерСтрой",
            "phone": "+79501234567",
            "first_name": "Сергей",
            "last_name": "Сидоров",
            "is_manager": True,
            "is_customer": False,
        },
    ]

    created_count = 0

    for data in demo_users:
        email = data["email"].strip().lower()

        # что положим в defaults при создании
        defaults = {
            "username": data["username"],
            "first_name": data.get("first_name", "") or "",
            "last_name": data.get("last_name", "") or "",
        }

        # кастомные поля (если есть в модели пользователя)
        for field in ("company_name", "phone"):
            if field in data:
                defaults[field] = data[field]

        user, was_created = User.objects.get_or_create(email=email, defaults=defaults)

        # Если уже был — обновим основные поля (удобно для демо)
        if not was_created:
            for k, v in defaults.items():
                setattr(user, k, v)

        # Пароль для демо: выставляем всегда одинаковый, чтобы вход работал после повторных запусков
        user.set_password(data["password"])

        # Доп. флаги — ставим только если такие поля реально есть в модели
        if hasattr(user, "email_confirmed"):
            user.email_confirmed = True

        if hasattr(user, "is_manager"):
            user.is_manager = bool(data.get("is_manager", False))

        if hasattr(user, "is_customer"):
            user.is_customer = bool(data.get("is_customer", True))

        user.save()

        if was_created:
            created_count += 1
            _out(stdout, f"✅ Создан: {user.username} ({getattr(user, 'company_name', '')})")
        else:
            _out(stdout, f"⚠️ Уже существует: {email} — обновил данные/пароль")

    _out(stdout, f"\nСоздано {created_count} новых пользователей")

    _out(stdout, "\nДанные для входа:")
    _out(stdout, "-----------------")
    _out(stdout, "Клиент 1:")
    _out(stdout, "  Логин: client_dgu")
    _out(stdout, "  Пароль: client123")
    _out(stdout, "  Email: dgu_client@industrial.com")
    _out(stdout, "")
    _out(stdout, "Клиент 2 (компрессор):")
    _out(stdout, "  Логин: client_compressor")
    _out(stdout, "  Пароль: client123")
    _out(stdout, "  Email: compressor_client@factory.ru")
    _out(stdout, "")
    _out(stdout, "Менеджер:")
    _out(stdout, "  Логин: manager1")
    _out(stdout, "  Пароль: manager123")
    _out(stdout, "  Email: manager@container-company.com")

    if stdout:
        stdout.write("seed_demo_users: done")

    return created_count
