from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import VendorOnboardingForm
from .models import VendorProfile

from locations.models import City
from listings.models import Listing
from bookings.models import Booking

@login_required
def onboarding(request):

    if request.user.role != request.user.Role.VENDOR:
        return redirect('core:home')

    vendor_profile = get_object_or_404(
        VendorProfile,
        user=request.user
    )

    # If onboarding is already completed,
    # don't allow the vendor to stay on onboarding page.
    if (
        vendor_profile.state_id
        and vendor_profile.city_id
        and vendor_profile.categories.exists()
    ):
        return redirect('vendors:dashboard')

    if request.method == 'POST':

        form = VendorOnboardingForm(
            request.POST,
            instance=vendor_profile
        )

        if form.is_valid():

            form.save()

            return redirect('vendors:dashboard')

    else:

        form = VendorOnboardingForm(
            instance=vendor_profile
        )

    return render(
        request,
        'vendors/onboarding.html',
        {
            'form': form,
            'vendor_profile': vendor_profile,
        }
    )


@login_required
def edit_profile(request):

    if request.user.role != request.user.Role.VENDOR:
        return redirect('core:home')

    vendor_profile = get_object_or_404(
        VendorProfile,
        user=request.user
    )

    if request.method == 'POST':

        form = VendorOnboardingForm(
            request.POST,
            instance=vendor_profile
        )

        if form.is_valid():

            form.save()

            return redirect('vendors:dashboard')

    else:

        form = VendorOnboardingForm(
            instance=vendor_profile
        )

    return render(
        request,
        'vendors/edit_profile.html',
        {
            'form': form,
            'vendor_profile': vendor_profile,
        }
    )


@login_required
def dashboard(request):

    if request.user.role != request.user.Role.VENDOR:
        return redirect('core:home')

    vendor_profile = get_object_or_404(
        VendorProfile,
        user=request.user
    )

    # =====================================================
    # VENDOR ONBOARDING CHECK
    # =====================================================

    if (
        not vendor_profile.state_id
        or not vendor_profile.city_id
        or not vendor_profile.categories.exists()
    ):
        return redirect('vendors:onboarding')

    # =====================================================
    # VENDOR LISTINGS
    # =====================================================

    vendor_listings = (
        Listing.objects
        .filter(
            vendor=vendor_profile
        )
        .select_related(
            'category',
            'city',
            'state',
        )
        .prefetch_related(
            'images',
        )
        .order_by(
            '-created_at'
        )
    )

    # =====================================================
    # LISTING COUNTS
    # =====================================================

    total_listings = vendor_listings.count()

    active_listings = (
        vendor_listings
        .filter(
            is_active=True
        )
        .count()
    )

    # =====================================================
    # LATEST LISTINGS
    # =====================================================

    latest_listings = vendor_listings[:3]

    # =====================================================
    # VENDOR BOOKINGS
    # =====================================================
    #
    # Vendor ki 2 types ki bookings ho sakti hain:
    #
    # 1. Listing booking
    # 2. Package booking
    #
    # Dono vendor ki bookings dashboard me dikhengi.
    #

    vendor_bookings = (
        Booking.objects
        .filter(
            Q(
                listing__vendor=vendor_profile
            )
            |
            Q(
                package__vendor=vendor_profile
            )
        )
        .select_related(
            'listing',
            'package',
            'group',
            'group__customer',
        )
        .order_by(
            '-created_at'
        )
    )

    # =====================================================
    # TOTAL BOOKINGS
    # =====================================================

    total_bookings = vendor_bookings.count()

    # =====================================================
    # RECENT BOOKINGS
    # =====================================================

    recent_bookings = vendor_bookings[:5]

    # =====================================================
    # RATING
    # =====================================================

    # Abhi verified review/rating relation nahi hai.
    # Isliye fake rating nahi dikhayenge.

    average_rating = None

    # =====================================================
    # ENQUIRIES
    # =====================================================

    # Abhi enquiry model verified nahi hai.

    enquiries_count = 0

    # =====================================================
    # RENDER
    # =====================================================

    return render(
        request,
        'vendors/dashboard.html',
        {
            # ---------------------------------------------
            # PROFILE
            # ---------------------------------------------

            'vendor_profile':
                vendor_profile,

            'phone_number':
                request.user.phone_number,

            'email':
                request.user.email,

            'full_name':
                request.user.full_name,

            # ---------------------------------------------
            # LISTINGS
            # ---------------------------------------------

            'listings':
                vendor_listings,

            'total_listings':
                total_listings,

            'active_listings':
                active_listings,

            'latest_listings':
                latest_listings,

            # ---------------------------------------------
            # BOOKINGS
            # ---------------------------------------------

            'total_bookings':
                total_bookings,

            'recent_bookings':
                recent_bookings,

            # ---------------------------------------------
            # OTHER DASHBOARD STATS
            # ---------------------------------------------

            'enquiries_count':
                enquiries_count,

            'average_rating':
                average_rating,
        }
    )
def cities_by_state(request):

    state_id = request.GET.get('state_id')

    if not state_id:
        return JsonResponse({
            'cities': []
        })

    cities = City.objects.filter(
        state_id=state_id,
        is_active=True
    ).values(
        'id',
        'name'
    )

    return JsonResponse({
        'cities': list(cities)
    })