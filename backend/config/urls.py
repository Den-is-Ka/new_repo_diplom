from django.http import HttpResponse
from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

urlpatterns = [
    path('', lambda request: HttpResponse('''
        <html>
        <head><title>Diplom Container Configurator</title></head>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h1>🚀 Diplom Container Configurator</h1>
            <p>✅ Django server is running successfully!</p>
            <h2>📋 Available endpoints:</h2>
            <ul>
                <li><a href="/admin/">🔐 Admin Panel</a></li>
                <li><a href="/api/docs/">📖 API Documentation (Swagger)</a></li>
                <li><a href="/api/redoc/">📚 API Documentation (ReDoc)</a></li>
                <li><a href="/api/catalog/equipment-types/">📦 Catalog API</a></li>
                <li><a href="/api/configurator/configurations/">⚙️ Configurator API</a></li>
                <li><a href="/api/token/">🔑 Get JWT Token</a></li>
            </ul>
        </body>
        </html>
    ''')),

    path('admin/', admin.site.urls),
    path('api/catalog/', include('catalog.urls')),
    path('api/users/', include('users.urls')),
    path('api/configurator/', include('configurator.urls')),
    path('api/auth/', include('rest_framework.urls')),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    path("api/orders/", include("orders.urls")),
]

from django.conf import settings
from django.conf.urls.static import static

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
