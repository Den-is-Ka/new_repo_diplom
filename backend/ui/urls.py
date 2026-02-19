from django.urls import path
from . import views

urlpatterns = [
    path("login/", views.login_page, name="ui-login"),
    path("customer/", views.customer_page, name="ui-customer"),
    path("manager/", views.manager_page, name="ui-manager"),
]
