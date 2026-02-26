import pytest

pytestmark = pytest.mark.django_db


def test_ui_login_page(client):
    r = client.get("/ui/login/")
    assert r.status_code in (200, 302)


def test_ui_customer_page(client):
    r = client.get("/ui/customer/")
    assert r.status_code in (200, 302)


def test_ui_orders_page(client):
    r = client.get("/ui/orders/")
    assert r.status_code in (200, 302)
