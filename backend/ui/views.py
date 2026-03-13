from django.shortcuts import render


def login_page(request):
    return render(request, "ui/login.html")


def logout_page(request):
    # JWT хранится на фронте (localStorage), “logout” делает JS.
    return render(request, "ui/logout.html")


def customer_page(request):
    return render(request, "ui/customer.html")


def orders_page(request):
    return render(request, "ui/orders.html")


def order_detail_page(request, order_id: int):
    return render(request, "ui/order_detail.html", {"order_id": order_id})
