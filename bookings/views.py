from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from listings.models import Listing

from .forms import BookingForm

from .models import BookingGroup

from payments.models import Payment
from django.db.models import Prefetch
from io import BytesIO
from django.db.models import Sum
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone
from xhtml2pdf import pisa

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
            "bookings__listing",
            "bookings__package",
            Prefetch(
                "payments",
                queryset=Payment.objects.filter(
                    status=Payment.Status.SUCCESS
                ).order_by("-paid_at", "-created_at"),
            ),
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
            Prefetch(
                "payments",
                queryset=Payment.objects.filter(
                    status=Payment.Status.SUCCESS
                ).order_by("-paid_at", "-created_at"),
            ),
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




@login_required
def booking_invoice(request, booking_id):
    booking_group = get_object_or_404(
        BookingGroup,
        id=booking_id,
        customer=request.user,
    )

    bookings = list(
        booking_group.bookings.select_related(
            "listing__vendor",
            "package__vendor",
        )
    )


    
    # Prepare actual pricing breakdown for every booked item.
    for booking in bookings:
        if booking.listing_id:
            listing = booking.listing
            rate = Decimal(str(listing.base_price))

            if listing.pricing_type == Listing.PricingType.PER_DAY:
                quantity = booking_group.total_days or 1
                unit_label = "day"
                calculation = (
                    f"INR {rate:,.2f} x {quantity} {unit_label}(s)"
                )

            elif listing.pricing_type == Listing.PricingType.PER_PLATE:
                quantity = booking_group.guest_count or 0
                unit_label = "guest/plate"
                calculation = (
                    f"INR {rate:,.2f} x {quantity} {unit_label}(s)"
                )

            else:
                quantity = 1
                unit_label = "fixed price"
                calculation = f"INR {rate:,.2f} - {unit_label}"

            booking.invoice_rate = rate
            booking.invoice_quantity = quantity
            booking.invoice_unit_label = unit_label
            booking.invoice_calculation = calculation
            booking.invoice_pricing_type = listing.get_pricing_type_display()

        elif booking.package_id:
            booking.invoice_rate = booking.item_price
            booking.invoice_quantity = 1
            booking.invoice_unit_label = "package"
            booking.invoice_calculation = "Fixed package price"
            booking.invoice_pricing_type = "Package Price"

        else:
            booking.invoice_rate = booking.item_price
            booking.invoice_quantity = 1
            booking.invoice_unit_label = "item"
            booking.invoice_calculation = "Price details unavailable"
            booking.invoice_pricing_type = "Price"


    payments = list(
        Payment.objects.filter(
            booking_group=booking_group,
            status=Payment.Status.SUCCESS,
        ).order_by("paid_at", "created_at")
    )

    total_paid = sum(
        (payment.amount for payment in payments),
        Decimal("0.00"),
    )

    total_amount = booking_group.total_amount or Decimal("0.00")

    remaining_balance = max(
        Decimal("0.00"),
        total_amount - total_paid,
    )

    context = {
        "booking_group": booking_group,
        "bookings": bookings,
        "payments": payments,
        "total_paid": total_paid,
        "remaining_balance": remaining_balance,
        "invoice_date": timezone.localdate(),
    }

    html = render_to_string(
        "bookings/invoice_pdf.html",
        context,
        request=request,
    )

    # HTML to PDF  convert .
    pdf_buffer = BytesIO()
    pdf_result = pisa.CreatePDF(
        html,
        dest=pdf_buffer,
        encoding="UTF-8",
    )

    if pdf_result.err:
        return HttpResponse(
            "Invoice PDF generate nahi ho paya. Please try again.",
            status=500,
        )

    response = HttpResponse(
        pdf_buffer.getvalue(),
        content_type="application/pdf",
    )

    invoice_number = (
        f"WB-{booking_group.created_at.year}-"
        f"{booking_group.id:06d}"
    )

    response["Content-Disposition"] = (
        f'attachment; filename="Invoice-{invoice_number}.pdf"'
    )

    return response
