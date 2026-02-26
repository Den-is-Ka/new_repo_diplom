from django.urls import path
from rest_framework.decorators import api_view
from rest_framework.response import Response


@api_view(["GET"])
def api_root(request):
    return Response(
        {
            "message": "notifications API",
            "status": "working",
            "available_endpoints": ["/api/notifications/", "/api/notifications/test/"],
        }
    )


@api_view(["GET"])
def test_endpoint(request):
    return Response(
        {
            "status": "success",
            "app": "notifications",
            "message": "API endpoint is working correctly",
        }
    )


urlpatterns = [
    path("", api_root, name="notifications-root"),
    path("test/", test_endpoint, name="notifications-test"),
]
