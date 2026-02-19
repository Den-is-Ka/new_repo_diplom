from django.contrib.auth.decorators import login_required
from django.shortcuts import render


def login_page(request):
    return render(request, "ui/login.html")


def customer_page(request):
    # JWT UI не требует django-login, поэтому без декоратора
    return render(request, "ui/customer.html")


def manager_page(request):
    return render(request, "ui/manager.html")
