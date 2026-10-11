import time
from datetime import datetime
from decimal import Decimal

import razorpay

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from bookings.models import BookingGroup, Booking
from listings.models import Listing
from django.urls import reverse


def get_razorpay_client():
    return razorpay.Client(
        auth=(
            settings.RAZORPAY_KEY_ID,
            settings.RAZORPAY_KEY_SECRET,
        )
    )


@login_required
def payment_page(request):

    booking_data = request.session.get("booking_data")

    if not booking_data:
        return redirect("listings:my_listings")

    start_date = datetime.strptime(
        booking_data["start_date"],
        "%Y-%m-%d"
    ).date()

    end_date = datetime.strptime(
        booking_data["end_date"],
        "%Y-%m-%d"
    ).date()

    listing = get_object_or_404(
        Listing.objects
        .select_related(
            "category",
            "state",
            "city",
            "vendor",
        )
        .prefetch_related(
            "images",
        ),
        id=booking_data["listing_id"],
        is_active=True,
    )

    amount = Decimal(str(listing.base_price))

    amount_paise = int(
        amount * Decimal("100")
    )

    client = get_razorpay_client()

    receipt = (
        f"wedbook_{request.user.id}_"
        f"{listing.id}_{int(time.time())}"
    )

    razorpay_order = client.order.create(
        data={
            "amount": amount_paise,
            "currency": "INR",
            "receipt": receipt,
            "notes": {
                "listing_id": str(listing.id),
                "customer_id": str(request.user.id),
            },
        }
    )

    request.session["razorpay_order_id"] = (
        razorpay_order["id"]
    )

    request.session["razorpay_amount"] = (
        amount_paise
    )



    return render(
        request,
        "payments/payment_page.html",
        {
            "listing": listing,
            "booking_data": booking_data,
            "start_date": start_date,
            "end_date": end_date,
            "amount": amount,
            "amount_paise": amount_paise,
            "razorpay_order_id": razorpay_order["id"],
            "razorpay_key_id": settings.RAZORPAY_KEY_ID,
        },
    )


@login_required
def verify_payment(request):

    if request.method != "POST":
        return JsonResponse(
            {
                "success": False,
                "message": "Invalid request method."
            },
            status=405,
        )

    booking_data = request.session.get(
        "booking_data"
    )

    if not booking_data:
        return JsonResponse(
            {
                "success": False,
                "message": "Booking session expired."
            },
            status=400,
        )

    razorpay_order_id = request.POST.get(
        "razorpay_order_id"
    )

    razorpay_payment_id = request.POST.get(
        "razorpay_payment_id"
    )

    razorpay_signature = request.POST.get(
        "razorpay_signature"
    )

    session_order_id = request.session.get(
        "razorpay_order_id"
    )

    if (
        not razorpay_order_id
        or not razorpay_payment_id
        or not razorpay_signature
    ):
        return JsonResponse(
            {
                "success": False,
                "message": "Payment details are incomplete."
            },
            status=400,
        )

    if razorpay_order_id != session_order_id:
        return JsonResponse(
            {
                "success": False,
                "message": "Invalid payment order."
            },
            status=400,
        )

    client = get_razorpay_client()

    try:

        client.utility.verify_payment_signature(
            {
                "razorpay_order_id":
                    razorpay_order_id,

                "razorpay_payment_id":
                    razorpay_payment_id,

                "razorpay_signature":
                    razorpay_signature,
            }
        )

    except razorpay.errors.SignatureVerificationError:

        return JsonResponse(
            {
                "success": False,
                "message": "Payment verification failed."
            },
            status=400,
        )

    listing = get_object_or_404(
        Listing,
        id=booking_data["listing_id"],
        is_active=True,
    )

    with transaction.atomic():

        booking_group = BookingGroup.objects.create(
    customer=request.user,

    full_name=booking_data.get(
        "full_name",
        "",
    ),

    phone_number=booking_data.get(
        "phone_number",
        "",
    ),

    email=booking_data.get(
        "email",
        "",
    ),

    event_start_date=booking_data[
        "start_date"
    ],

    event_end_date=booking_data[
        "end_date"
    ],

    guest_count=booking_data[
        "guest_count"
    ],

    notes=booking_data.get(
        "customer_note",
        "",
    ),
)
        Booking.objects.create(
            group=booking_group,
            listing=listing,
            status=Booking.Status.CONFIRMED,
        )

    request.session.pop(
        "booking_data",
        None,
    )

    request.session.pop(
        "razorpay_order_id",
        None,
    )

    request.session.pop(
        "razorpay_amount",
        None,
    )

    request.session["payment_success"] = True

    return JsonResponse(
        {
            "success": True,
            "redirect_url": reverse(
            "payments:payment_success"
            ),
        }
    )


@login_required
def payment_success(request):

    success = request.session.pop(
        "payment_success",
        False,
    )

    if not success:
        return redirect(
            "listings:my_listings"
        )

    return render(
        request,
        "payments/payment_success.html",
    )