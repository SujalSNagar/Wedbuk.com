from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
import time
import razorpay
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from requests import request
from bookings.models import BookingGroup, Booking
from listings.models import Listing
from .models import Payment

MIN_ADVANCE_PERCENTAGE = 20
CENT = Decimal("0.01")

def get_razorpay_client():
    return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

def calculate_total(listing, start_date, end_date, guest_count):
    rate = Decimal(str(listing.base_price))
    if listing.pricing_type == Listing.PricingType.PER_DAY:
        units = (end_date - start_date).days + 1
        rate *= Decimal(units)
    elif listing.pricing_type == Listing.PricingType.PER_PLATE:
        if not guest_count or int(guest_count) < 1:
            raise ValueError("Guest count is required for per-plate pricing.")
        rate *= Decimal(int(guest_count))
    return rate.quantize(CENT, rounding=ROUND_HALF_UP)

def booking_context(request):
    data = request.session.get("booking_data")
    if not data:
        return None
    try:
        start = datetime.strptime(data["start_date"], "%Y-%m-%d").date()
        end = datetime.strptime(data["end_date"], "%Y-%m-%d").date()
        if end < start:
            return None
        listing = get_object_or_404(Listing.objects.select_related("category", "state", "city", "vendor").prefetch_related("images"), pk=data["listing_id"], is_active=True)
        total = calculate_total(listing, start, end, data.get("guest_count"))
        if total <= 0:
            return None
        return data, listing, start, end, total
    except (KeyError, TypeError, ValueError):
        return None

def create_order(total, percentage, listing, user):
    percentage = int(percentage)
    if not MIN_ADVANCE_PERCENTAGE <= percentage <= 100:
        raise ValueError("Advance percentage must be between 20 and 100.")
    payable = (total * Decimal(percentage) / Decimal(100)).quantize(CENT, rounding=ROUND_HALF_UP)
    paise = int(payable * 100)
    order = get_razorpay_client().order.create(data={
        "amount": paise, "currency": "INR",
        "receipt": f"wb_{user.id}_{listing.id}_{int(time.time())}"[:40],
        "notes": {"listing_id": str(listing.id), "customer_id": str(user.id), "advance_percentage": str(percentage), "total_amount": str(total)},
    })
    return order, payable, total - payable, paise

@login_required
@require_POST
def payment_page(request):
    ctx = booking_context(request)

    if not ctx:
        return redirect("listings:my_listings")

    data, listing, start, end, total = ctx

    initial_amount = (
        total * Decimal("0.20")
    ).quantize(CENT, rounding=ROUND_HALF_UP)

    remaining = total - initial_amount

    return render(request, "payments/payment_page.html", {
        "listing": listing,
        "booking_data": data,
        "start_date": start,
        "end_date": end,
        "amount": initial_amount,
        "amount_paise": int(initial_amount * 100),
        "total_amount": total,
        "remaining_amount": remaining,
        "advance_percentage": 20,
        "min_advance_percentage": MIN_ADVANCE_PERCENTAGE,
        "razorpay_key_id": settings.RAZORPAY_KEY_ID,
    })

@login_required
@require_POST
def create_payment_order(request):
    ctx = booking_context(request)
    if not ctx:
        return JsonResponse({"success": False, "message": "Booking session expired."}, status=400)
    data, listing, start, end, total = ctx
    try:

        percentage = int(request.POST.get("percentage", "20"))
        
        if percentage < 20 or percentage > 100 or (percentage - 20) % 5 != 0:
            return JsonResponse({
                "success": False,
                "message": "Advance percentage must be between 20% and 100%, in steps of 5%."
            }, status=400)
        
        order, payable, remaining, paise = create_order(
            total, percentage, listing, request.user
        )

    except ValueError as exc:
        return JsonResponse({"success": False, "message": str(exc)}, status=400)
    except Exception:
        return JsonResponse({"success": False, "message": "Could not create payment order. Please retry."}, status=502)
    request.session["razorpay_order_id"] = order["id"]
    request.session["razorpay_amount"] = paise
    request.session["razorpay_percentage"] = percentage
    request.session["razorpay_total_amount"] = str(total)
    return JsonResponse({"success": True, "order_id": order["id"], "amount_paise": paise, "amount": str(payable), "total_amount": str(total), "remaining_amount": str(remaining), "percentage": percentage})

@login_required
@require_POST
def verify_payment(request):
    ctx = booking_context(request)
    if not ctx:
        return JsonResponse({"success": False, "message": "Booking session expired."}, status=400)
    data, listing, start, end, total = ctx
    order_id = request.POST.get("razorpay_order_id")
    payment_id = request.POST.get("razorpay_payment_id")
    signature = request.POST.get("razorpay_signature")
    expected_order = request.session.get("razorpay_order_id")
    expected_paise = request.session.get("razorpay_amount")
    percentage = request.session.get("razorpay_percentage")
    expected_total = request.session.get("razorpay_total_amount")
    if not all([order_id, payment_id, signature, expected_order, expected_paise, percentage, expected_total]):
        return JsonResponse({"success": False, "message": "Payment details are incomplete."}, status=400)
    if order_id != expected_order or Decimal(expected_total) != total:
        return JsonResponse({"success": False, "message": "Payment order does not match this booking."}, status=400)
    client = get_razorpay_client()
    try:
        client.utility.verify_payment_signature({"razorpay_order_id": order_id, "razorpay_payment_id": payment_id, "razorpay_signature": signature})
        remote_payment = client.payment.fetch(payment_id)
        if str(remote_payment.get("order_id")) != order_id or int(remote_payment.get("amount", 0)) != int(expected_paise) or remote_payment.get("status") != "captured":
            return JsonResponse({"success": False, "message": "Payment is not captured or amount does not match."}, status=400)
    except razorpay.errors.SignatureVerificationError:
        return JsonResponse({"success": False, "message": "Payment signature verification failed."}, status=400)
    except Exception:
        return JsonResponse({"success": False, "message": "Unable to verify payment with Razorpay. If money was deducted, contact support."}, status=502)
    percentage = int(percentage)
    paid = (total * Decimal(percentage) / Decimal(100)).quantize(CENT, rounding=ROUND_HALF_UP)
    remaining = total - paid
    try:
        with transaction.atomic():
            existing = Payment.objects.filter(transaction_id=payment_id).first()
            if existing:
                request.session["payment_success"] = True
                request.session["payment_amount"] = str(existing.amount)
                request.session["payment_total_amount"] = str(total)
                request.session["payment_remaining_amount"] = str(remaining)
                request.session["payment_percentage"] = percentage
                return JsonResponse({"success": True, "redirect_url": reverse("payments:payment_success")})
            group = BookingGroup.objects.create(
                customer=request.user,
                full_name=data.get("full_name", ""),
                phone_number=data.get("phone_number", ""),
                email=data.get("email", ""),
                event_start_date=start,
                event_end_date=end,
                guest_count=data.get("guest_count") or None,
                notes=data.get("customer_note", ""),
                total_amount=total,
                selected_payment_percentage=percentage,
                amount_paid=paid,
                remaining_amount=remaining,
            )
            Booking.objects.create(group=group, listing=listing, status=Booking.Status.CONFIRMED)
            Payment.objects.create(booking_group=group, amount=paid,
                payment_type=Payment.PaymentType.FULL if percentage == 100 else Payment.PaymentType.ADVANCE,
                status=Payment.Status.SUCCESS, advance_percentage=percentage,
                razorpay_order_id=order_id, transaction_id=payment_id, paid_at=timezone.now())
    except Exception:
        return JsonResponse({"success": False, "message": f"Payment was verified but booking could not be saved. Contact support with payment ID {payment_id}."}, status=500)
    for key in ("booking_data", "razorpay_order_id", "razorpay_amount", "razorpay_percentage", "razorpay_total_amount"):
        request.session.pop(key, None)
    request.session["payment_success"] = True
    request.session["payment_amount"] = str(paid)
    request.session["payment_total_amount"] = str(total)
    request.session["payment_remaining_amount"] = str(remaining)
    request.session["payment_percentage"] = percentage
    return JsonResponse({"success": True, "redirect_url": reverse("payments:payment_success")})

@login_required
def payment_success(request):
    if not request.session.pop("payment_success", False):
        return redirect("listings:my_listings")
    context = {key: request.session.pop(key, None) for key in ("payment_amount", "payment_total_amount", "payment_remaining_amount", "payment_percentage")}
    return render(request, "payments/payment_success.html", context)
