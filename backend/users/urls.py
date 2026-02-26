from django.urls import path
from .register_api import RegisterView
from rest_framework_simplejwt.views import TokenVerifyView

urlpatterns = [
    # Здесь можно добавить endpoints для пользователей
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path("register/", RegisterView.as_view(), name="register"),
]
