from django.urls import path
from drf_spectacular.utils import extend_schema  # ✅ добавили
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.routers import DefaultRouter

from .views import OrderViewSet

router = DefaultRouter()
router.register(r"orders", OrderViewSet, basename="orders")


@extend_schema(exclude=True)  # ✅ исключаем из OpenAPI, чтобы не было warning
@api_view(["GET"])
def api_root(request):
    return Response(
        {
            "message": "orders API",
            "status": "working",
            "available_endpoints": [
                "/api/orders/",
                "/api/orders/test/",
                "/api/orders/orders/",
                "/api/orders/orders/?status=NEW",
                "/api/orders/orders/{id}/",
                "/api/orders/orders/my/",
                "/api/orders/orders/manager/?status=NEW",
                "/api/orders/orders/{id}/assign_manager/",
                "/api/orders/orders/{id}/change_status/",
                "/api/orders/orders/{id}/history/",
            ],
        }
    )


@extend_schema(exclude=True)  # ✅ исключаем из OpenAPI, чтобы не было warning
@api_view(["GET"])
def test_endpoint(request):
    return Response(
        {
            "status": "success",
            "app": "orders",
            "message": "API endpoint is working correctly",
        }
    )


urlpatterns = [
    path("", api_root, name="orders-root"),
    path("test/", test_endpoint, name="orders-test"),
] + router.urls
