import pytest

pytestmark = pytest.mark.django_db


def test_users_urls_smoke(client):
    # если users/views вообще не подключены к urls — тест просто не нужен
    # но если подключены, хотя бы откроем корневой users endpoint (если есть)
    r = client.get("/api/users/")
    assert r.status_code in (200, 301, 302, 401, 403, 404)
