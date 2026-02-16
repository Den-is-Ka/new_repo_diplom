from django.urls import include, path
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.routers import DefaultRouter

from .views import OrderViewSet


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
                "/api/orders/orders/{id}/",
            ],
        }
    )


@api_view(["GET"])
def test_endpoint(request):
    return Response(
        {
            "status": "success",
            "app": "orders",
            "message": "API endpoint is working correctly",
        }
    )


router = DefaultRouter()
router.register(r"orders", OrderViewSet, basename="order")

urlpatterns = [
    path("", api_root, name="orders-root"),
    path("test/", test_endpoint, name="orders-test"),
    path("", include(router.urls)),
]
