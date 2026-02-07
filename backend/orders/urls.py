from django.urls import path
from rest_framework.response import Response
from rest_framework.decorators import api_view

@api_view(['GET'])
def api_root(request):
    return Response({
        "message": "orders API",
        "status": "working",
        "available_endpoints": [
            "/api/orders/",
            "/api/orders/test/"
        ]
    })

@api_view(['GET'])
def test_endpoint(request):
    return Response({
        "status": "success",
        "app": "orders",
        "message": "API endpoint is working correctly"
    })

urlpatterns = [
    path('', api_root, name='orders-root'),
    path('test/', test_endpoint, name='orders-test'),
]
