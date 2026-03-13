import pytest
from django.contrib.auth.models import Group
from rest_framework.test import APIClient

from orders.models import Order, OrderStatus

pytestmark = pytest.mark.django_db


def make_user(
    User,
    username: str,
    company_name: str,
    password: str = "1234",
    *,
    is_staff: bool = False,
):
    """
    Твой кастомный User требует company_name (и у тебя есть email/phone в модели).
    """
    u = User(
        username=username,
        company_name=company_name,
        email=f"{username}@mail.ru",
        phone="+7 900 000-00-00",
        is_staff=is_staff,
        is_superuser=is_staff,
    )
    u.set_password(password)
    u.save()
    return u


def auth(client: APIClient, user):
    client.force_authenticate(user=user)
    return client


def test_manufacturer_sees_all_orders(django_user_model):
    User = django_user_model
    client = APIClient()

    manufacturer = make_user(User, "manu", "ООО Производитель")
    g, _ = Group.objects.get_or_create(name="manufacturer")
    manufacturer.groups.add(g)

    customer_a = make_user(User, "cust_a", "ООО Клиент A")
    customer_b = make_user(User, "cust_b", "ООО Клиент B")

    Order.objects.create(
        user=customer_a,
        order_number="ORD-T1",
        status=OrderStatus.NEW,
        total_price=1,
        snapshot={},
    )
    Order.objects.create(
        user=customer_b,
        order_number="ORD-T2",
        status=OrderStatus.NEW,
        total_price=1,
        snapshot={},
    )

    r = auth(client, manufacturer).get("/api/orders/orders/")
    assert r.status_code == 200
    assert r.data["count"] == 2


def test_client_sees_only_own_orders_and_cannot_retrieve_foreign(django_user_model):
    User = django_user_model
    client = APIClient()

    customer = make_user(User, "cust1", "ООО Клиент 1")
    other = make_user(User, "cust2", "ООО Клиент 2")

    own = Order.objects.create(
        user=customer,
        order_number="ORD-OWN",
        status=OrderStatus.NEW,
        total_price=1,
        snapshot={},
    )
    foreign = Order.objects.create(
        user=other,
        order_number="ORD-FOR",
        status=OrderStatus.NEW,
        total_price=1,
        snapshot={},
    )

    r = auth(client, customer).get("/api/orders/orders/")
    assert r.status_code == 200
    assert r.data["count"] == 1
    assert r.data["results"][0]["order_number"] == own.order_number

    # В твоей реализации ожидаем 404 (из-за фильтрации get_queryset)
    r2 = auth(client, customer).get(f"/api/orders/orders/{foreign.id}/")
    assert r2.status_code == 404


def test_client_cannot_change_status(django_user_model):
    User = django_user_model
    client = APIClient()

    manufacturer = make_user(User, "manu3", "ООО Производитель 3")
    g, _ = Group.objects.get_or_create(name="manufacturer")
    manufacturer.groups.add(g)

    customer = make_user(User, "cust3", "ООО Клиент 3")
    order = Order.objects.create(
        user=customer,
        order_number="ORD-CS",
        status=OrderStatus.NEW,
        total_price=1,
        snapshot={},
    )

    r = auth(client, customer).post(
        f"/api/orders/orders/{order.id}/change_status/",
        {"status": "IN_REVIEW", "comment": "пытаюсь"},
        format="json",
    )
    assert r.status_code == 403


def test_manufacturer_lifecycle_and_invalid_transition(django_user_model):
    User = django_user_model
    client = APIClient()

    manufacturer = make_user(User, "manu2", "ООО Производитель 2")
    g, _ = Group.objects.get_or_create(name="manufacturer")
    manufacturer.groups.add(g)

    customer = make_user(User, "custx", "ООО Клиент X")
    order = Order.objects.create(
        user=customer,
        order_number="ORD-LC",
        status=OrderStatus.NEW,
        total_price=1,
        snapshot={},
    )

    c = auth(client, manufacturer)

    # NEW -> IN_REVIEW
    r = c.post(
        f"/api/orders/orders/{order.id}/change_status/",
        {"status": "IN_REVIEW", "comment": "ok"},
        format="json",
    )
    assert r.status_code == 200
    assert r.data["status"] == "IN_REVIEW"

    # IN_REVIEW -> APPROVED (quoted_at должен появиться)
    r = c.post(
        f"/api/orders/orders/{order.id}/change_status/",
        {"status": "APPROVED"},
        format="json",
    )
    assert r.status_code == 200
    assert r.data["status"] == "APPROVED"
    assert r.data["quoted_at"] is not None

    # APPROVED -> IN_PRODUCTION
    r = c.post(
        f"/api/orders/orders/{order.id}/change_status/",
        {"status": "IN_PRODUCTION"},
        format="json",
    )
    assert r.status_code == 200
    assert r.data["status"] == "IN_PRODUCTION"

    # IN_PRODUCTION -> COMPLETED (completed_at должен появиться)
    r = c.post(
        f"/api/orders/orders/{order.id}/change_status/",
        {"status": "COMPLETED"},
        format="json",
    )
    assert r.status_code == 200
    assert r.data["status"] == "COMPLETED"
    assert r.data["completed_at"] is not None

    # invalid: COMPLETED -> IN_PRODUCTION
    r = c.post(
        f"/api/orders/orders/{order.id}/change_status/",
        {"status": "IN_PRODUCTION"},
        format="json",
    )
    assert r.status_code == 400
