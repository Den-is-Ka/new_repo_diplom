from django.urls import path

from . import views

app_name = "ui"

urlpatterns = [
    path("login/", views.login_page, name="login"),
    path("logout/", views.logout_page, name="logout"),
    path("customer/", views.customer_page, name="customer"),
    # ✅ ВАЖНО: сначала список
    path("orders/", views.orders_page, name="orders"),
    # ✅ потом детали
    path("orders/<int:order_id>/", views.order_detail_page, name="order_detail"),
]
