from django.urls import path
from rest_framework_simplejwt.views import TokenVerifyView
from . import views

urlpatterns = [
    # Здесь можно добавить endpoints для пользователей
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),
]
