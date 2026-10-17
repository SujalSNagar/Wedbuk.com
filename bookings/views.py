from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from listings.models import Listing

from .forms import BookingForm

from .models import BookingGroup




from decimal import Decimal


def calculate_booking_total(listing, start_date, end_date, guest_count=0):
    """Calculate booking price from the listing's pricing type."""

    if not start_date or not end_date or end_date < start_date:
        return {
            "total_days": 0,
            "unit_price": listing.base_price,
            "total_amount": listing.base_price,
        }

    # Both start and end dates are included.
    total_days = (end_date - start_date).days + 1
    unit_price = listing.base_price

    if listing.pricing_type == Listing.PricingType.PER_DAY:
        total_amount = unit_price * total_days

    elif listing.pricing_type == Listing.PricingType.PER_PLATE:
        total_amount = unit_price * int(guest_count or 0)

    else:
        total_amount = unit_price

    return {
        "total_days": total_days,
        "unit_price": unit_price,
        "total_amount": total_amount.quantize(Decimal("0.01")),
    }



@login_required
def booking_page(request, listing_id):

    listing = get_object_or_404(
        Listing.objects
        .select_related(
            "category",
            "state",
            "city",
            "service",
        )
        .prefetch_related(
            "images",
            "videos",
        ),
        id=listing_id,
        is_active=True,
    )

    if request.method == "POST":

        form = BookingForm(
            request.POST,
            listing=listing,
        )


        if form.is_valid():
            start_date = form.cleaned_data["start_date"]
            end_date = form.cleaned_data["end_date"]
            guest_count = form.cleaned_data["guest_count"]

            price_data = calculate_booking_total(
                listing,
                start_date,
                end_date,
                guest_count,
            )

            request.session["booking_data"] = {
                "listing_id": listing.id,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "guest_count": guest_count,
                "customer_note": form.cleaned_data["customer_note"],
                "full_name": form.cleaned_data["full_name"],
                "phone_number": form.cleaned_data["phone_number"],
                "email": form.cleaned_data["email"],
                "total_days": price_data["total_days"],
                "unit_price": str(price_data["unit_price"]),
                "total_amount": str(price_data["total_amount"]),
                "pricing_type": listing.pricing_type,
            }

            request.session.modified = True

            return redirect("bookings:review_booking")


    else:
        booking_data = request.session.get("booking_data", {})

        start_date = request.GET.get("start_date") or booking_data.get("start_date")
        end_date = request.GET.get("end_date") or booking_data.get("end_date")

        form = BookingForm(
            initial={
                "start_date": start_date,
                "end_date": end_date,
                "guest_count": booking_data.get("guest_count"),
                "customer_note": booking_data.get("customer_note", ""),
                "full_name": booking_data.get(
                    "full_name",
                    request.user.full_name
                ),
                "phone_number": booking_data.get(
                    "phone_number",
                    request.user.phone_number
                ),
                "email": booking_data.get(
                    "email",
                    request.user.email
                ),
            },
            listing=listing,
        )
    # -----------------------------------------
    # Dates for displaying on booking page
    # -----------------------------------------

    start_date = form["start_date"].value()
    end_date = form["end_date"].value()

    if start_date:
        try:
            start_date = datetime.strptime(
                str(start_date),
                "%Y-%m-%d"
            ).date()
        except (ValueError, TypeError):
            start_date = None

    if end_date:
        try:
            end_date = datetime.strptime(
                str(end_date),
                "%Y-%m-%d"
            ).date()
        except (ValueError, TypeError):
            end_date = None


    
    guest_value = form["guest_count"].value()

    try:
        guest_count = int(guest_value) if guest_value else 0
    except (ValueError, TypeError):
        guest_count = 0

    price_data = calculate_booking_total(
        listing,
        start_date,
        end_date,
        guest_count,
    )


    return render(
        request,
        "bookings/booking_page.html",
        {
            "listing": listing,
            "form": form,
            "start_date": start_date,
            "end_date": end_date,
            "total_days": price_data["total_days"],
            "unit_price": price_data["unit_price"],
            "total_amount": price_data["total_amount"],
        },
    )


@login_required
def review_booking(request):

    booking_data = request.session.get("booking_data")

    if not booking_data:
        return redirect("listings:my_listings")

    listing = get_object_or_404(
        Listing.objects
        .select_related(
            "category",
            "state",
            "city",
            "service",
        )
        .prefetch_related(
            "images",
            "videos",
        ),
        id=booking_data["listing_id"],
        is_active=True,
    )

    start_date = datetime.strptime(
    booking_data["start_date"],
    "%Y-%m-%d"
    ).date()

    end_date = datetime.strptime(
        booking_data["end_date"],
        "%Y-%m-%d"
    ).date()


    guest_count = int(booking_data.get("guest_count") or 0)

    price_data = calculate_booking_total(
        listing,
        start_date,
        end_date,
        guest_count,
    )


    return render(
        request,
        "bookings/review_booking.html",
        {
            "listing": listing,
            "booking_data": booking_data,
            "start_date": start_date,
            "end_date": end_date,
            "total_days": price_data["total_days"],
            "unit_price": price_data["unit_price"],
            "total_amount": price_data["total_amount"],

        },
    )



@login_required
def my_bookings(request):

    booking_groups = (
        BookingGroup.objects
        .filter(customer=request.user)
        .prefetch_related(
            'bookings__listing',
            'bookings__package',
        )
    )

    return render(
        request,
        'bookings/my_bookings.html',
        {
            'booking_groups': booking_groups,
        }
    )


@login_required
def booking_detail(request, booking_id):

    booking_group = get_object_or_404(
        BookingGroup.objects
        .prefetch_related(
            "bookings__listing",
            "bookings__package",
        ),
        id=booking_id,
        customer=request.user,
    )

    return render(
        request,
        "bookings/booking_detail.html",
        {
            "booking_group": booking_group,
        },
    )