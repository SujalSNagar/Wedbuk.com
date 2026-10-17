from django.urls import path
from . import views

app_name = "payments"
urlpatterns = [
    path("", views.payment_page, name="payment"),
    path("create-order/", views.create_payment_order, name="create_payment_order"),
    path("verify/", views.verify_payment, name="verify_payment"),
    path("success/", views.payment_success, name="payment_success"),

    path(
    "create-order/",
    views.create_payment_order,
    name="create_payment_order",
),
]
