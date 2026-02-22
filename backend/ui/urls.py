from django.urls import path
from . import views

app_name = "ui"

urlpatterns = [
    path("login/", views.login_page, name="login"),
    path("logout/", views.logout_page, name="logout"),

    # клиентский конфигуратор
    path("customer/", views.customer_page, name="customer"),

    # производитель / менеджер
    path("orders/", views.orders_page, name="orders"),
    path("orders/<int:order_id>/", views.order_detail_page, name="order-detail"),
]