from django.urls import path

from . import views


app_name = "bookings"


urlpatterns = [

    path(
        "book/<int:listing_id>/",
        views.booking_page,
        name="booking_page",
    ),

path(
    "review/",
    views.review_booking,
    name="review_booking",
),

path(
    'my-bookings/',
    views.my_bookings,
    name='my_bookings'
),

path(
    "my-bookings/<int:booking_id>/",
    views.booking_detail,
    name="booking_detail",
),
]