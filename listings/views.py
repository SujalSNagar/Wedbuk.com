from datetime import date, timedelta, datetime

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import JsonResponse, request
from django.shortcuts import get_object_or_404, redirect, render

from categories.models import Category, CategoryAttribute
from locations.models import City,State
from vendors.models import VendorProfile
from bookings.models import Booking

from .forms import (
    ListingForm,
    ListingImageForm,
    ListingAvailabilityForm,
    ListingBlockedDateForm,
)

from .models import (
    Listing,
    ListingImage,
    ListingVideo,
    ListingAttributeValue,
    ListingAvailability,
    ListingBlockedDate,
)


from django.db.models import Q

from packages.models import Package


# =========================================================
# LISTING DETAIL
# =========================================================

def listing_detail(request, listing_id):

    listing = get_object_or_404(
        Listing.objects
        .select_related(
            'vendor',
            'vendor__city',
            'vendor__state',
            'category',
            'city',
            'state',
        )
        .prefetch_related(
            'images',
            'videos',
            'event_types',
            'services',
            'availability_periods',
            'blocked_dates',
            'attribute_values__attribute',
        ),
        id=listing_id,
        is_active=True,
    )

    return render(
        request,
        'listings/listing_detail.html',
        {
            'listing': listing
        }
    )


# =========================================================
# ADD LISTING
# =========================================================

@login_required
def add_listing(request):

    if request.user.role != request.user.Role.VENDOR:
        return redirect('core:home')

    vendor_profile = get_object_or_404(
        VendorProfile,
        user=request.user
    )

    if request.method == 'POST':

        form = ListingForm(
            request.POST,
            request.FILES,
            vendor_profile=vendor_profile
        )

        if form.is_valid():

            try:

                with transaction.atomic():

                    listing = form.save(
                        commit=False
                    )

                    listing.vendor = vendor_profile

                    listing.save()

                    form.save_m2m()

                    # Save dynamic category attributes
                    save_listing_attributes(
                        listing,
                        form
                    )

                    # =====================================
                    # GALLERY IMAGES
                    # =====================================

                    gallery_images = (
                        request.FILES
                        .getlist('gallery_images')
                    )[:8]

                    for index, image in enumerate(
                        gallery_images,
                        start=1
                    ):

                        ListingImage.objects.create(
                            listing=listing,
                            image=image,
                            display_order=index
                        )

                    # =====================================
                    # GALLERY VIDEOS
                    # =====================================

                    gallery_videos = (
                        request.FILES
                        .getlist('gallery_videos')
                    )[:2]

                    for index, video in enumerate(
                        gallery_videos,
                        start=1
                    ):

                        video_obj = ListingVideo(
                            listing=listing,
                            video=video,
                            display_order=index
                        )

                        video_obj.full_clean()

                        video_obj.save()

                    # =====================================
                    # AVAILABILITY
                    # =====================================

                    available_from = request.POST.get(
                        'available_from'
                    )

                    available_until = request.POST.get(
                        'available_until'
                    )

                    if (
                        available_from
                        and available_until
                    ):

                        availability = ListingAvailability(
                            listing=listing,
                            available_from=available_from,
                            available_until=available_until,
                            is_active=True
                        )

                        availability.full_clean()

                        availability.save()

                return redirect(
                    'listings:my_listings'
                )

            except ValidationError as exc:
                for message in _collect_validation_messages(exc):
                    form.add_error(None, message)

    else:

        form = ListingForm(vendor_profile=vendor_profile)

    return render(
        request,
        'listings/add_listing.html',
        {
            'form': form,
            'vendor_profile': vendor_profile,
            'dynamic_attribute_fields':
                get_dynamic_attribute_fields(form),
        }
    )


# =========================================================
# EDIT LISTING
# =========================================================

def _collect_validation_messages(exc):
    if hasattr(exc, 'message_dict'):
        messages = []
        for field, errors in exc.message_dict.items():
            for error in errors:
                messages.append(
                    error if field == '__all__' else f'{field}: {error}'
                )
        return messages
    return exc.messages



def update_existing_availability(request, listing):
    """Existing availability periods ko usi record mein update karta hai."""

    for period in listing.availability_periods.all():

        pid = period.id

        date_from = request.POST.get(f'availability_from_{pid}')
        date_until = request.POST.get(f'availability_until_{pid}')

        # Ye period form mein bheja hi nahi gaya
        if date_from is None or date_until is None:
            continue

        date_from = date_from.strip()
        date_until = date_until.strip()

        if not (date_from and date_until):
            raise ValidationError(
                'Availability dates cannot be empty.'
            )

        period.available_from = date_from
        period.available_until = date_until
        period.is_active = (
            f'availability_active_{pid}' in request.POST
        )

        period.full_clean()
        period.save()


def update_existing_blocked_dates(request, listing):

    for blocked in listing.blocked_dates.all():

        bid = blocked.id

        new_date = request.POST.get(f'blocked_date_{bid}')

        if new_date is None:
            continue

        new_date = new_date.strip()

        if not new_date:
            raise ValidationError('Blocked date cannot be empty.')

        reason = request.POST.get(
            f'blocked_reason_{bid}', ''
        ).strip()

        blocked.date = new_date
        blocked.reason = reason

        blocked.full_clean()  
        blocked.save()


@login_required
def edit_listing(request, listing_id):

    if request.user.role != request.user.Role.VENDOR:
        return redirect('core:home')

    vendor_profile = get_object_or_404(
        VendorProfile,
        user=request.user
    )

    listing = get_object_or_404(
        Listing,
        id=listing_id,
        vendor=vendor_profile
    )

    if request.method == 'POST':

        form = ListingForm(
            request.POST,
            request.FILES,
            instance=listing,
            vendor_profile=vendor_profile
        )

        if form.is_valid():

            try:

                with transaction.atomic():

                    # commit=True par m2m (services, event_types)
                    # apne aap save ho jata hai, save_m2m() ki zarurat nahi
                    listing = form.save()

                    save_listing_attributes(listing, form)

                    # ---------- NEW GALLERY IMAGES ----------
                    remaining_image_slots = max(
                        0, 8 - listing.images.count()
                    )

                    gallery_images = request.FILES.getlist(
                        'gallery_images'
                    )[:remaining_image_slots]

                    last_order = (
                        listing.images
                        .order_by('-display_order')
                        .values_list('display_order', flat=True)
                        .first()
                        or 0
                    )

                    for index, image in enumerate(
                        gallery_images,
                        start=last_order + 1
                    ):
                        ListingImage.objects.create(
                            listing=listing,
                            image=image,
                            display_order=index
                        )

                    # ---------- NEW VIDEOS ----------
                    remaining_video_slots = max(
                        0, 2 - listing.videos.count()
                    )

                    gallery_videos = request.FILES.getlist(
                        'gallery_videos'
                    )[:remaining_video_slots]

                    last_video_order = (
                        listing.videos
                        .order_by('-display_order')
                        .values_list('display_order', flat=True)
                        .first()
                        or 0
                    )

                    for index, video in enumerate(
                        gallery_videos,
                        start=last_video_order + 1
                    ):
                        video_obj = ListingVideo(
                            listing=listing,
                            video=video,
                            display_order=index
                        )
                        video_obj.full_clean()
                        video_obj.save()


                    # ---------- NEW AVAILABILITY ----------
                    update_existing_availability(request, listing)
                    update_existing_blocked_dates(request, listing)

                    available_from = request.POST.get(
                        'available_from', ''
                    ).strip()
                    available_until = request.POST.get(
                        'available_until', ''
                    ).strip()

                    if available_from or available_until:

                        if not (available_from and available_until):
                            raise ValidationError(
                                'Please select both Available From '
                                'and Available Until dates.'
                            )

                        already_exists = listing.availability_periods.filter(
                            available_from=available_from,
                            available_until=available_until
                        ).exists()

                        if already_exists:
                            raise ValidationError(
                                'This availability period already exists.'
                            )

                        availability = ListingAvailability(
                            listing=listing,
                            available_from=available_from,
                            available_until=available_until,
                            is_active=True
                        )
                        availability.full_clean()
                        availability.save()

                    # ---------- NEW BLOCKED DATE ----------
                    new_blocked_date = request.POST.get(
                        'new_blocked_date', ''
                    ).strip()

                    if new_blocked_date:

                        blocked_reason = request.POST.get(
                            'blocked_date_reason', ''
                        ).strip()

                        already_blocked = (
                            listing.blocked_dates
                            .filter(date=new_blocked_date)
                            .exists()
                        )

                        if not already_blocked:
                            blocked = ListingBlockedDate(
                                listing=listing,
                                date=new_blocked_date,
                                reason=blocked_reason
                            )
                            blocked.full_clean()
                            blocked.save()

                return redirect(
                    'listings:listing_detail',
                    listing_id=listing.id
                )

            except ValidationError as exc:

                for message in _collect_validation_messages(exc):
                    form.add_error(None, message)

    else:

        form = ListingForm(
            instance=listing,
            vendor_profile=vendor_profile
        )

    return render(
        request,
        'listings/edit_listing.html',
        {
            'form': form,
            'listing': listing,
            'vendor_profile': vendor_profile,
            'remaining_image_slots': max(0, 8 - listing.images.count()),
            'dynamic_attribute_fields':
                get_dynamic_attribute_fields(form),
        }
    )

# =========================================================
# MY LISTINGS
# =========================================================

@login_required
def my_listings(request):

    if request.user.role != request.user.Role.VENDOR:
        return redirect('core:home')

    vendor_profile = get_object_or_404(
        VendorProfile,
        user=request.user
    )

    listings = (
        Listing.objects
        .filter(
            vendor=vendor_profile
        )
        .select_related(
            'category',
            'state',
            'city'
        )
        .prefetch_related(
            'images',
            'videos',
            'services'
        )
    )

    active_count = listings.filter(
        is_active=True
    ).count()

    return render(
        request,
        'listings/my_listings.html',
        {
            'listings': listings,
            'vendor_profile': vendor_profile,
            'active_count': active_count,
        }
    )


# =========================================================
# DELETE LISTING
# =========================================================

@login_required
def delete_listing(
    request,
    listing_id
):

    if request.user.role != request.user.Role.VENDOR:
        return redirect('core:home')

    vendor_profile = get_object_or_404(
        VendorProfile,
        user=request.user
    )

    listing = get_object_or_404(
        Listing,
        id=listing_id,
        vendor=vendor_profile
    )

    if request.method == 'POST':

        listing.delete()

        return redirect(
            'listings:my_listings'
        )

    return render(
        request,
        'listings/delete_listing.html',
        {
            'listing': listing,
        }
    )


# =========================================================
# ADD LISTING IMAGE
# =========================================================

@login_required
def add_listing_image(
    request,
    listing_id
):

    if request.user.role != request.user.Role.VENDOR:
        return redirect('core:home')

    vendor_profile = get_object_or_404(
        VendorProfile,
        user=request.user
    )

    listing = get_object_or_404(
        Listing,
        id=listing_id,
        vendor=vendor_profile
    )

    if request.method == 'POST':

        form = ListingImageForm(
            request.POST,
            request.FILES
        )

        if listing.images.count() >= 8:

            form.add_error(
                'image',
                'A listing can have maximum 8 gallery images.'
            )

        elif form.is_valid():

            image = form.save(
                commit=False
            )

            image.listing = listing

            image.display_order = (
                listing.images
                .order_by(
                    '-display_order'
                )
                .values_list(
                    'display_order',
                    flat=True
                )
                .first()
                or 0
            ) + 1

            image.save()

            return redirect(
                'listings:edit_listing',
                listing_id=listing.id
            )

    else:

        form = ListingImageForm()

    return render(
        request,
        'listings/add_listing_image.html',
        {
            'form': form,
            'listing': listing,
        }
    )



@login_required
def delete_cover_image(request, listing_id):

    if request.user.role != request.user.Role.VENDOR:
        return JsonResponse(
            {"success": False},
            status=403
        )

    vendor_profile = get_object_or_404(
        VendorProfile,
        user=request.user
    )

    listing = get_object_or_404(
        Listing,
        id=listing_id,
        vendor=vendor_profile
    )

    if request.method != "POST":
        return JsonResponse(
            {"success": False},
            status=405
        )

    if listing.cover_image:
        listing.cover_image.delete(save=False)
        listing.cover_image = ""
        listing.save(update_fields=["cover_image"])

    return JsonResponse({
        "success": True
    })


# =========================================================
# DELETE LISTING IMAGE
# =========================================================

@login_required
def delete_listing_image(
    request,
    image_id
):

    if request.user.role != request.user.Role.VENDOR:
        return redirect('core:home')

    vendor_profile = get_object_or_404(
        VendorProfile,
        user=request.user
    )

    image = get_object_or_404(
        ListingImage.objects.select_related(
            'listing'
        ),
        id=image_id,
        listing__vendor=vendor_profile
    )

    listing_id = image.listing.id

    if request.method == 'POST':

        image.delete()

    return redirect(
        'listings:edit_listing',
        listing_id=listing_id
    )


# =========================================================
# DELETE LISTING VIDEO
# =========================================================

@login_required
def delete_listing_video(
    request,
    video_id
):

    if request.user.role != request.user.Role.VENDOR:
        return redirect('core:home')

    vendor_profile = get_object_or_404(
        VendorProfile,
        user=request.user
    )

    video = get_object_or_404(
        ListingVideo.objects.select_related(
            'listing'
        ),
        id=video_id,
        listing__vendor=vendor_profile
    )

    listing_id = video.listing.id

    if request.method == 'POST':

        video.delete()

    return redirect(
        'listings:edit_listing',
        listing_id=listing_id
    )


# =========================================================
# ADD AVAILABILITY
# =========================================================

@login_required
def add_availability(
    request,
    listing_id
):

    if request.user.role != request.user.Role.VENDOR:
        return redirect('core:home')

    vendor_profile = get_object_or_404(
        VendorProfile,
        user=request.user
    )

    listing = get_object_or_404(
        Listing,
        id=listing_id,
        vendor=vendor_profile
    )

    if request.method == 'POST':

        form = ListingAvailabilityForm(
            request.POST
        )

        if form.is_valid():

            availability = form.save(
                commit=False
            )

            availability.listing = listing

            availability.save()

            return redirect(
                'listings:edit_listing',
                listing_id=listing.id
            )

    else:

        form = ListingAvailabilityForm()

    return render(
        request,
        'listings/add_availability.html',
        {
            'form': form,
            'listing': listing,
        }
    )


# =========================================================
# DELETE AVAILABILITY
# =========================================================

@login_required
def delete_availability(
    request,
    availability_id
):

    if request.user.role != request.user.Role.VENDOR:
        return redirect('core:home')

    vendor_profile = get_object_or_404(
        VendorProfile,
        user=request.user
    )

    availability = get_object_or_404(
        ListingAvailability.objects.select_related(
            'listing'
        ),
        id=availability_id,
        listing__vendor=vendor_profile
    )

    listing_id = availability.listing.id

    if request.method == 'POST':

        availability.delete()

    return redirect(
        'listings:edit_listing',
        listing_id=listing_id
    )


# =========================================================
# ADD BLOCKED DATE
# =========================================================

@login_required
def add_blocked_date(
    request,
    listing_id
):

    if request.user.role != request.user.Role.VENDOR:
        return redirect('core:home')

    vendor_profile = get_object_or_404(
        VendorProfile,
        user=request.user
    )

    listing = get_object_or_404(
        Listing,
        id=listing_id,
        vendor=vendor_profile
    )

    if request.method == 'POST':

        form = ListingBlockedDateForm(
            request.POST
        )

        if form.is_valid():

            blocked_date = form.save(
                commit=False
            )

            blocked_date.listing = listing

            try:

                blocked_date.save()

            except Exception:

                form.add_error(
                    'date',
                    'This date is already blocked.'
                )

            else:

                return redirect(
                    'listings:edit_listing',
                    listing_id=listing.id
                )

    else:

        form = ListingBlockedDateForm()

    return render(
        request,
        'listings/add_blocked_date.html',
        {
            'form': form,
            'listing': listing,
        }
    )


# =========================================================
# DELETE BLOCKED DATE
# =========================================================

@login_required
def delete_blocked_date(
    request,
    blocked_date_id
):

    if request.user.role != request.user.Role.VENDOR:
        return redirect('core:home')

    vendor_profile = get_object_or_404(
        VendorProfile,
        user=request.user
    )

    blocked_date = get_object_or_404(
        ListingBlockedDate.objects.select_related(
            'listing'
        ),
        id=blocked_date_id,
        listing__vendor=vendor_profile
    )

    listing_id = blocked_date.listing.id

    if request.method == 'POST':

        blocked_date.delete()

    return redirect(
        'listings:edit_listing',
        listing_id=listing_id
    )


# =========================================================
# AVAILABILITY CALENDAR
# =========================================================

def availability_calendar(
    request,
    listing_id
):

    listing = get_object_or_404(
        Listing,
        id=listing_id,
        is_active=True
    )

    selected_month = request.GET.get(
        'month'
    )

    if selected_month:

        try:

            year, month = selected_month.split('-')

            year = int(year)
            month = int(month)

        except (
            ValueError,
            TypeError
        ):

            return JsonResponse(
                {
                    'error':
                        'Invalid month format. Use YYYY-MM.'
                },
                status=400
            )

    else:

        today = date.today()

        year = today.year
        month = today.month

    available_periods = (
        ListingAvailability.objects
        .filter(
            listing=listing,
            is_active=True
        )
        .values(
            'available_from',
            'available_until'
        )
    )

    blocked_dates = (
        ListingBlockedDate.objects
        .filter(
            listing=listing
        )
        .values_list(
            'date',
            flat=True
        )
    )

    blocked_set = {
        blocked_date.isoformat()
        for blocked_date in blocked_dates
    }

    available_from = []
    available_until = []

    for period in available_periods:

        available_from.append(
            period['available_from']
        )

        available_until.append(
            period['available_until']
        )

    if (
        available_from
        and available_until
    ):

        minimum_date = min(
            available_from
        )

        maximum_date = max(
            available_until
        )

    else:

        minimum_date = None
        maximum_date = None

    return JsonResponse(
        {
            'listing_id': listing.id,

            'month':
                f'{year:04d}-{month:02d}',

            'available_from': (
                minimum_date.isoformat()
                if minimum_date
                else None
            ),

            'available_until': (
                maximum_date.isoformat()
                if maximum_date
                else None
            ),

            'blocked_dates':
                sorted(blocked_set),
        }
    )


# =========================================================
# SEARCH
# =========================================================

# =========================================================
# SEARCH
# =========================================================

def search(request):

    # =====================================================
    # BASE QUERY
    # =====================================================

    listings = (
        Listing.objects
        .filter(
            is_active=True
        )
        .select_related(
            'vendor',
            'vendor__state',
            'vendor__city',
            'category',
            'state',
            'city',
        )
        .prefetch_related(
            'images',
            'videos',
            'services',
            'event_types',
            'attribute_values__attribute',
        )
    )


    # =====================================================
    # GET PARAMETERS
    # =====================================================

    query = request.GET.get(
        'q',
        ''
    ).strip()

    category_slug = request.GET.get(
        'category',
        ''
    ).strip()

    event_slug = request.GET.get(
        'event',
        ''
    ).strip()

    city = request.GET.get(
        'city',
        ''
    ).strip()

    service_slug = request.GET.get(
        'service',
        ''
    ).strip()

    state = request.GET.get(
        'state',
        ''
    ).strip()

    guests = request.GET.get(
        'guests',
        ''
    ).strip()

    min_price = request.GET.get(
        'min_price',
        ''
    ).strip()

    max_price = request.GET.get(
        'max_price',
        ''
    ).strip()

    pricing_type = request.GET.get(
        'pricing_type',
        ''
    ).strip()


    # =====================================================
    # MAIN SEARCH
    # =====================================================

    if query:

        listings = listings.filter(
            Q(
                title__icontains=query
            )
            |
            Q(
                description__icontains=query
            )
            |
            Q(
                vendor__business_name__icontains=query
            )
            |
            Q(
                category__name__icontains=query
            )
            |
            Q(
                services__name__icontains=query
            )
            |
            Q(
                city__name__icontains=query
            )
            |
            Q(
                state__name__icontains=query
            )
            |
            Q(
                vendor__city__name__icontains=query
            )
            |
            Q(
                vendor__state__name__icontains=query
            )
        )


    # =====================================================
    # EXISTING CATEGORY
    # =====================================================

    if category_slug:

        listings = listings.filter(
            category__slug=category_slug
        )


    # =====================================================
    # EVENT
    # =====================================================

    if event_slug:

        listings = listings.filter(
            event_types__slug=event_slug
        )


    # =====================================================
    # CITY
    #
    # Sidebar sends city ID.
    # Old search may send city name.
    # Support both.
    # =====================================================

    if city:

        if city.isdigit():

            listings = listings.filter(
                Q(city_id=city)
                |
                Q(vendor__city_id=city)
            )

        else:

            listings = listings.filter(
                Q(city__name__icontains=city)
                |
                Q(vendor__city__name__icontains=city)
            )


    # =====================================================
    # SERVICE
    # =====================================================

    if service_slug:

        listings = listings.filter(
            services__slug=service_slug
        )


    # =====================================================
    # STATE
    # =====================================================

    if state:

        if state.isdigit():

            listings = listings.filter(
                Q(state_id=state)
                |
                Q(vendor__state_id=state)
            )

        else:

            listings = listings.filter(
                Q(state__name__icontains=state)
                |
                Q(vendor__state__name__icontains=state)
            )


    # =====================================================
    # GUEST RANGE
    # =====================================================

    guest_min = None
    guest_max = None

    if guests == "100":

        guest_max = 99

    elif guests == "250":

        guest_min = 100
        guest_max = 250

    elif guests == "500":

        guest_min = 250
        guest_max = 500

    elif guests == "1000":

        guest_min = 500
        guest_max = 1000

    elif guests == "1000+":

        guest_min = 1001


    if guest_min is not None:

        listings = listings.filter(
            Q(max_guests__isnull=True)
            |
            Q(max_guests__gte=guest_min)
        )


    if guest_max is not None:

        listings = listings.filter(
            Q(min_guests__isnull=True)
            |
            Q(min_guests__lte=guest_max)
        )


    # =====================================================
    # PRICE
    # =====================================================

    try:

        min_price_value = (
            float(min_price)
            if min_price
            else None
        )

    except ValueError:

        min_price_value = None


    try:

        max_price_value = (
            float(max_price)
            if max_price
            else None
        )

    except ValueError:

        max_price_value = None


    if min_price_value is not None:

        listings = listings.filter(
            base_price__gte=min_price_value
        )


    if max_price_value is not None:

        listings = listings.filter(
            base_price__lte=max_price_value
        )


    # =====================================================
    # DYNAMIC ADMIN ATTRIBUTES
    # =====================================================

    attribute_filters = {}

    for key in request.GET:

        if not key.startswith(
            'attribute_'
        ):
            continue

        try:

            attribute_id = int(
                key.split(
                    '_',
                    1
                )[1]
            )

        except (
            ValueError,
            IndexError
        ):

            continue


        values = [
            value.strip()
            for value in request.GET.getlist(
                key
            )
            if value.strip()
        ]


        if values:

            attribute_filters[
                attribute_id
            ] = values


    for attribute_id, values in attribute_filters.items():

        listings = listings.filter(
            attribute_values__attribute_id=attribute_id,
            attribute_values__value__in=values,
        )


    # =====================================================
    # REMOVE DUPLICATES
    # =====================================================

    listings = listings.distinct()


    # =====================================================
    # RESULT COUNT
    # =====================================================

    result_count = listings.count()


    # =====================================================
    # FILTER DATA
    # =====================================================

    cities = (
        City.objects
        .filter(
            is_active=True
        )
        .order_by(
            'name'
        )
    )


    categories = (
        Category.objects
        .filter(
            is_active=True
        )
        .order_by(
            'name'
        )
    )


    filter_attributes = []

    for attribute in (
        CategoryAttribute.objects
        .order_by(
            'order',
            'id'
        )
    ):

        options = [
            option.strip()
            for option in (
                attribute.options or ''
            ).split(',')
            if option.strip()
        ]

        filter_attributes.append({

            'id': attribute.id,

            'label': attribute.label,

            'field_type':
                attribute.field_type,

            'options':
                options,

            'unit':
                attribute.unit,
        })


    # =====================================================
    # SELECTED ATTRIBUTE VALUES
    # =====================================================

    selected_attribute_values = {}

    for attribute_id, values in attribute_filters.items():

        selected_attribute_values[
            str(attribute_id)
        ] = values


    # =====================================================
    # RENDER
    # =====================================================

    return render(
        request,
        'listings/search.html',
        {

            'listings':
                listings,

            # Search
            'query':
                query,

            # Existing search filters
            'selected_category':
                category_slug,

            'selected_event':
                event_slug,

            'selected_city':
                city,

            'selected_service':
                service_slug,

            'selected_state':
                state,

            # Result info
            'result_count':
                result_count,

            # Sidebar data
            'cities':
                cities,

            'categories':
                categories,

            'filter_attributes':
                filter_attributes,

            # Selected filter values
            'selected_city_id':
                city,

            'selected_guests':
                guests,

            'selected_min_price':
                min_price,

            'selected_max_price':
                max_price,

            'selected_pricing_type':
                pricing_type,

            'selected_categories':
                request.GET.getlist(
                    'category'
                ),

            'selected_services':
                request.GET.getlist(
                    'service'
                ),

            'selected_attribute_values':
                selected_attribute_values,
        }
    )
# =========================================================
# CATEGORY ATTRIBUTES API
# =========================================================

def category_attributes(request):

    category_id = request.GET.get(
        'category_id'
    )

    if not category_id:

        return JsonResponse(
            {
                'attributes': []
            }
        )

    attributes = (
        CategoryAttribute.objects
        .filter(
            category_id=category_id
        )
        .order_by(
            'order',
            'id'
        )
    )

    data = []

    for attribute in attributes:

        options = [
            option.strip()
            for option in (
                attribute.options or ''
            ).split(',')
            if option.strip()
        ]

        data.append(
            {
                'id': attribute.id,
                'label': attribute.label,
                'field_type':
                    attribute.field_type,
                'options': options,
                'unit': attribute.unit,
                'help_text':
                    attribute.help_text,
            }
        )

    return JsonResponse(
        {
            'attributes': data
        }
    )

# =========================================================
# CATEGORY DETAIL
# =========================================================

# =========================================================
# CATEGORY DETAIL
# =========================================================

def category_detail(request, slug):

    from categories.models import Category

    category = get_object_or_404(
        Category,
        slug=slug,
        is_active=True
    )

    # =====================================================
    # FILTER VALUES
    # =====================================================

    city_id = request.GET.get(
        "city",
        ""
    ).strip()

    guests = request.GET.get(
        "guests",
        ""
    ).strip()

    min_price = request.GET.get(
        "min_price",
        ""
    ).strip()

    max_price = request.GET.get(
        "max_price",
        ""
    ).strip()

    pricing_type = request.GET.get(
        "pricing_type",
        ""
    ).strip()

    service_slugs = request.GET.getlist(
        "service"
    )

    # =====================================================
    # DYNAMIC ATTRIBUTE FILTERS
    # =====================================================

    attribute_filters = {}

    for key in request.GET:

        if not key.startswith("attribute_"):
            continue

        try:

            attribute_id = int(
                key.split("_", 1)[1]
            )

        except (
            ValueError,
            IndexError
        ):

            continue

        values = [
            value.strip()
            for value in request.GET.getlist(key)
            if value.strip()
        ]

        if values:
            attribute_filters[attribute_id] = values

    # =====================================================
    # GUEST RANGE
    # =====================================================

    guest_min = None
    guest_max = None

    if guests == "100":

        guest_max = 99

    elif guests == "250":

        guest_min = 100
        guest_max = 250

    elif guests == "500":

        guest_min = 250
        guest_max = 500

    elif guests == "1000":

        guest_min = 500
        guest_max = 1000

    elif guests == "1000+":

        guest_min = 1001

    # =====================================================
    # PRICE
    # =====================================================

    try:

        min_price_value = (
            float(min_price)
            if min_price
            else None
        )

    except ValueError:

        min_price_value = None

    try:

        max_price_value = (
            float(max_price)
            if max_price
            else None
        )

    except ValueError:

        max_price_value = None

    # =====================================================
    # LISTINGS
    # =====================================================

    listings = (
        Listing.objects
        .filter(
            category=category,
            is_active=True
        )
        .select_related(
            "vendor",
            "vendor__state",
            "vendor__city",
            "category",
            "state",
            "city",
        )
        .prefetch_related(
            "images",
            "videos",
            "services",
            "event_types",
            "attribute_values__attribute",
        )
        .order_by("-created_at")
    )

    # =====================================================
    # CITY
    # =====================================================

    if city_id:

        listings = listings.filter(
            city_id=city_id
        )

    # =====================================================
    # GUEST CAPACITY
    # =====================================================

    if guest_min is not None:

        listings = listings.filter(
            Q(max_guests__isnull=True)
            |
            Q(max_guests__gte=guest_min)
        )

    if guest_max is not None:

        listings = listings.filter(
            Q(min_guests__isnull=True)
            |
            Q(min_guests__lte=guest_max)
        )

    # =====================================================
    # PRICE
    # =====================================================

    if min_price_value is not None:

        listings = listings.filter(
            base_price__gte=min_price_value
        )

    if max_price_value is not None:

        listings = listings.filter(
            base_price__lte=max_price_value
        )

    # =====================================================
    # PRICING TYPE
    # =====================================================
    #
    # Apply only if Listing has pricing_type field.
    #

    if pricing_type:

        listings = listings.filter(
            pricing_type=pricing_type
        )

    # =====================================================
    # SERVICES
    # =====================================================

    if service_slugs:

        listings = listings.filter(
            services__slug__in=service_slugs
        )

    # =====================================================
    # DYNAMIC ATTRIBUTES
    # =====================================================
    #
    # Every selected attribute must match.
    #
    # Example:
    #
    # Food Preference = Vegetarian
    # Venue Type = Resort
    #
    # BOTH conditions must match.
    #

    for attribute_id, values in attribute_filters.items():

        listings = listings.filter(
            attribute_values__attribute_id=attribute_id,
            attribute_values__value__in=values,
        )

    listings = listings.distinct()

    # =====================================================
    # CITIES
    # =====================================================

    cities = (
        City.objects
        .filter(
            is_active=True
        )
        .order_by("name")
    )

    # =====================================================
    # FILTER ATTRIBUTES
    # =====================================================

    filter_attributes = []

    for attribute in (
        CategoryAttribute.objects
        .order_by(
            "order",
            "id"
        )
    ):

        options = [
            option.strip()
            for option in (
                attribute.options or ""
            ).split(",")
            if option.strip()
        ]

        filter_attributes.append(
            {
                "id": attribute.id,
                "label": attribute.label,
                "field_type":
                    attribute.field_type,
                "options": options,
                "unit":
                    attribute.unit,
                "help_text":
                    attribute.help_text,
            }
        )

    # =====================================================
    # SELECTED ATTRIBUTE VALUES
    # =====================================================

    selected_attribute_values = {}

    for attribute_id, values in attribute_filters.items():

        selected_attribute_values[
            str(attribute_id)
        ] = values

    # =====================================================
    # RENDER
    # =====================================================

    return render(
        request,
        "listings/category_detail.html",
        {
            "category":
                category,

            "listings":
                listings,

            "cities":
                cities,

            "filter_attributes":
                filter_attributes,

            "selected_city_id":
                city_id,

            "selected_guests":
                guests,

            "selected_min_price":
                min_price,

            "selected_max_price":
                max_price,

            "selected_pricing_type":
                pricing_type,

            "selected_services":
                service_slugs,

            "selected_attribute_values":
                selected_attribute_values,
        }
    )
# =========================================================
# DYNAMIC ATTRIBUTE FIELDS
# =========================================================

def get_dynamic_attribute_fields(form):

    result = []

    for field_name in form.fields:

        if not field_name.startswith(
            'attribute_'
        ):
            continue

        try:

            attribute_id = int(
                field_name.split(
                    '_',
                    1
                )[1]
            )

        except (
            ValueError,
            IndexError
        ):

            continue

        attribute = (
            CategoryAttribute.objects
            .filter(
                id=attribute_id
            )
            .first()
        )

        if attribute:

            result.append(
                (
                    attribute,
                    form[field_name]
                )
            )

    return result


# =========================================================
# CITIES BY STATE
# =========================================================

def cities_by_state(request):

    state_id = request.GET.get(
        'state_id'
    )

    if not state_id:

        return JsonResponse(
            {
                'cities': []
            }
        )

    cities = (
        City.objects
        .filter(
            state_id=state_id,
            is_active=True
        )
        .values(
            'id',
            'name'
        )
    )

    return JsonResponse(
        {
            'cities': list(cities)
        }
    )


# =========================================================
# LISTING AVAILABILITY
# =========================================================

def listing_availability(
    request,
    listing_id
):

    listing = get_object_or_404(
        Listing,
        id=listing_id,
        is_active=True
    )

    # =====================================================
    # AVAILABILITY PERIODS
    # =====================================================

    availability_periods = list(
        listing.availability_periods
        .filter(
            is_active=True
        )
        .values(
            'available_from',
            'available_until'
        )
    )

    # =====================================================
    # VENDOR BLOCKED DATES
    # =====================================================

    blocked_dates = list(
        listing.blocked_dates
        .values_list(
            'date',
            flat=True
        )
    )

    # =====================================================
    # BOOKED DATE RANGES
    # =====================================================

    bookings = (
        Booking.objects
        .filter(
            listing=listing,
            status=Booking.Status.CONFIRMED
        )
        .select_related(
            'group'
        )
    )

    booked_dates = set()

    for booking in bookings:

        start_date = (
            booking.group.event_start_date
        )

        end_date = (
            booking.group.event_end_date
        )

        current_date = start_date

        while current_date <= end_date:

            booked_dates.add(
                current_date.isoformat()
            )

            current_date += timedelta(
                days=1
            )

    return JsonResponse(
        {
            'listing_id': listing.id,

            'availability_periods': [
                {
                    'from':
                        period[
                            'available_from'
                        ].isoformat(),

                    'until':
                        period[
                            'available_until'
                        ].isoformat(),
                }

                for period
                in availability_periods
            ],

            'blocked_dates': [
                blocked_date.isoformat()

                for blocked_date
                in blocked_dates
            ],

            'booked_dates':
                list(booked_dates),
        }
    )


# =========================================================
# SAVE DYNAMIC LISTING ATTRIBUTES
# =========================================================

def save_listing_attributes(
    listing,
    form
):

    attributes = (
        CategoryAttribute.objects
        .filter(
            category=listing.category
        )
        .order_by(
            'order',
            'id'
        )
    )

    # Remove values that belong to an old category
    ListingAttributeValue.objects.filter(
        listing=listing
    ).exclude(
        attribute__category=listing.category
    ).delete()

    for attribute in attributes:

        field_name = (
            f'attribute_{attribute.id}'
        )

        value = form.cleaned_data.get(
            field_name
        )

        # Vendor fields are optional.
        # Empty values are simply removed.
        if (
            value is None
            or value == ''
        ):

            ListingAttributeValue.objects.filter(
                listing=listing,
                attribute=attribute
            ).delete()

            continue

        # Store boolean values consistently.
        if attribute.field_type == 'boolean':

            value = (
                'true'
                if value == 'true'
                else 'false'
            )

        else:

            value = str(value)

        ListingAttributeValue.objects.update_or_create(
            listing=listing,
            attribute=attribute,
            defaults={
                'value': value
            }
        )

# =========================================================
# BUDGET PLANNER RESULTS
# =========================================================

# =========================================================
# BUDGET PLANNER RESULTS
# =========================================================

def budget_results(request):

    state_id = request.GET.get("state", "").strip()
    city_id = request.GET.get("city", "").strip()
    guests = request.GET.get("guests", "").strip()
    budget = request.GET.get("budget", "").strip()
    event_date = request.GET.get("date","").strip()

    event_end_date = request.GET.get("end_date","").strip()

    category_slugs = request.GET.getlist("category")


    # =====================================================
    # GUEST COUNT
    # =====================================================

    if guests:

        try:
            guest_count = int(guests)

        except ValueError:
            guest_count = None

    else:
        guest_count = None


    # =====================================================
    # BUDGET
    # =====================================================

    if budget:

        try:
            budget_amount = float(budget)

        except ValueError:
            budget_amount = None

    else:
        budget_amount = None


    # =====================================================
    # DATE
    # =====================================================

    selected_date = None
    selected_end_date = None
    
    
    if event_date:
        try:
        
            selected_date = datetime.strptime(
                event_date,
                "%Y-%m-%d"
            ).date()
    
        except ValueError:
        
            selected_date = None
    
    
    if event_end_date:
        try:
        
            selected_end_date = datetime.strptime(
                event_end_date,
                "%Y-%m-%d"
            ).date()
    
        except ValueError:
        
            selected_end_date = None
    
    
    # Only start date selected
    # -> treat it as a single-day event
    if selected_date and not selected_end_date:
    
        selected_end_date = selected_date
    
    
    # Invalid date range
    if (
        selected_date
        and selected_end_date
        and selected_end_date < selected_date
    ):
    
        selected_end_date = None


    # =====================================================
    # LISTINGS - BASE QUERY
    # =====================================================

    listing_queryset = (
        Listing.objects
        .filter(is_active=True)
        .select_related(
            "vendor",
            "vendor__state",
            "vendor__city",
            "category",
        )
        .prefetch_related(
            "images",
            "services",
        )
    )


    # -----------------------------------------------------
    # LOCATION
    # -----------------------------------------------------

    if state_id:

        listing_queryset = listing_queryset.filter(
            state_id=state_id
        )


    if city_id:

        listing_queryset = listing_queryset.filter(
            city_id=city_id
        )


    # -----------------------------------------------------
    # CATEGORY
    # -----------------------------------------------------

    if category_slugs:

        listing_queryset = listing_queryset.filter(
            category__slug__in=category_slugs
        )


    # -----------------------------------------------------
    # GUEST CAPACITY
    # -----------------------------------------------------

    if guest_count is not None:

        minimum_required_capacity = max(
            guest_count - 50,
            0
        )

        listing_queryset = listing_queryset.filter(
            Q(min_guests__isnull=True) |
            Q(min_guests__lte=guest_count)
        ).filter(
            Q(max_guests__isnull=True) |
            Q(max_guests__gte=minimum_required_capacity)
        )


    # -----------------------------------------------------
    # DATE
    # -----------------------------------------------------

    if selected_date:

        listing_queryset = listing_queryset.filter(
            availability_periods__is_active=True,
            availability_periods__available_from__lte=selected_date,
            availability_periods__available_until__gte=selected_end_date,
        )


        # Exclude listings having any blocked date
        # inside the selected event range.
        listing_queryset = listing_queryset.exclude(
            blocked_dates__date__gte=selected_date,
            blocked_dates__date__lte=selected_end_date,
        )


        # Exclude listings having any confirmed booking
        # overlapping the selected event range.
        listing_queryset = listing_queryset.exclude(
            bookings__status="confirmed",
            bookings__group__event_start_date__lte=selected_end_date,
            bookings__group__event_end_date__gte=selected_date,
        )


    listing_queryset = listing_queryset.distinct()


    # =====================================================
    # PACKAGES - BASE QUERY
    # =====================================================

    package_queryset = (
        Package.objects
        .filter(is_active=True)
        .select_related(
            "vendor",
            "vendor__state",
            "vendor__city",
        )
        .prefetch_related(
            "package_categories__category",
            "package_categories__services",
            "gallery_images",
        )
    )


    # -----------------------------------------------------
    # LOCATION
    # -----------------------------------------------------

    if state_id:

        package_queryset = package_queryset.filter(
            vendor__state_id=state_id
        )


    if city_id:

        package_queryset = package_queryset.filter(
            vendor__city_id=city_id
        )


    # -----------------------------------------------------
    # GUEST CAPACITY
    # -----------------------------------------------------

    if guest_count is not None:

        minimum_required_capacity = max(
            guest_count - 50,
            0
        )

        package_queryset = package_queryset.filter(
            Q(min_guests__isnull=True) |
            Q(min_guests__lte=guest_count)
        ).filter(
            Q(max_guests__isnull=True) |
            Q(max_guests__gte=minimum_required_capacity)
        )


    # -----------------------------------------------------
    # CATEGORY
    # -----------------------------------------------------

    if category_slugs:

        package_queryset = package_queryset.filter(
            package_categories__category__slug__in=category_slugs
        )


    package_queryset = package_queryset.distinct()


    # =====================================================
    # RESULTS WITHIN SELECTED BUDGET
    # =====================================================

    if budget_amount is not None:

        listings = listing_queryset.filter(
            base_price__lte=budget_amount
        )

        packages = package_queryset.filter(
            price__lte=budget_amount
        )

    else:

        listings = listing_queryset
        packages = package_queryset


    # =====================================================
    # COUNTS
    # =====================================================

    listing_count = listings.count()
    package_count = packages.count()

    total_matches = (
        listing_count +
        package_count
    )


    # =====================================================
    # BUDGET SUGGESTION
    # =====================================================

    suggested_budget = None
    suggested_listing_count = 0
    suggested_package_count = 0
    suggested_total_matches = 0

    if (
        budget_amount is not None
        and total_matches == 0
    ):

        # ---------------------------------------------
        # Find cheapest listing above current budget
        # ---------------------------------------------

        next_listing = (
            listing_queryset
            .filter(
                base_price__gt=budget_amount
            )
            .order_by("base_price")
            .values_list(
                "base_price",
                flat=True
            )
            .first()
        )


        # ---------------------------------------------
        # Find cheapest package above current budget
        # ---------------------------------------------

        next_package = (
            package_queryset
            .filter(
                price__gt=budget_amount
            )
            .order_by("price")
            .values_list(
                "price",
                flat=True
            )
            .first()
        )


        # ---------------------------------------------
        # Find lowest available next price
        # ---------------------------------------------

        possible_prices = []

        if next_listing is not None:
            possible_prices.append(
                float(next_listing)
            )

        if next_package is not None:
            possible_prices.append(
                float(next_package)
            )


        if possible_prices:

            suggested_budget = min(
                possible_prices
            )


            # -----------------------------------------
            # How many options become available?
            # -----------------------------------------

            suggested_listing_count = (
                listing_queryset
                .filter(
                    base_price__lte=suggested_budget
                )
                .count()
            )

            suggested_package_count = (
                package_queryset
                .filter(
                    price__lte=suggested_budget
                )
                .count()
            )

            suggested_total_matches = (
                suggested_listing_count +
                suggested_package_count
            )


    # =====================================================
    # CONTEXT
    # =====================================================

    return render(
        request,
        "listings/budget_results.html",
        {
            "listings": listings,
            "packages": packages,

            "guest_count": guest_count,
            "budget_amount": budget_amount,
            "selected_date": selected_date,
            "selected_end_date": selected_end_date,

            "category_slugs": category_slugs,

            "selected_state_id": state_id,
            "selected_city_id": city_id,

            # Current result count
            "listing_count": listing_count,
            "package_count": package_count,
            "total_matches": total_matches,

            # Budget suggestion
            "suggested_budget": suggested_budget,
            "suggested_listing_count":
                suggested_listing_count,
            "suggested_package_count":
                suggested_package_count,
            "suggested_total_matches":
                suggested_total_matches,

        }
    )

    state_id = request.GET.get("state", "").strip()
    city_id = request.GET.get("city", "").strip()
    guests = request.GET.get("guests", "").strip()
    budget = request.GET.get("budget", "").strip()
    event_date = request.GET.get("date", "").strip()

    category_slugs = request.GET.getlist("category")


    # =====================================================
    # LISTINGS
    # =====================================================

    listings = (
        Listing.objects
        .filter(is_active=True)
        .select_related(
            "vendor",
            "vendor__state",
            "vendor__city",
            "category",
        )
        .prefetch_related(
            "images",
            "services",
        )
    )


    # -----------------------------------------------------
    # LOCATION
    # -----------------------------------------------------

    if state_id:
        listings = listings.filter(
            state_id=state_id
        )

    if city_id:
        listings = listings.filter(
            city_id=city_id
        )


    # -----------------------------------------------------
    # CATEGORIES
    # -----------------------------------------------------

    if category_slugs:
        listings = listings.filter(
            category__slug__in=category_slugs
        )


    # -----------------------------------------------------
    # GUEST CAPACITY
    # -----------------------------------------------------

    if guests:

        try:

            guest_count = int(guests)

            # User ke selected guests se 50 kam tak
            # capacity acceptable hai.
            minimum_required_capacity = max(
                guest_count - 50,
                0
            )

            listings = listings.filter(
                Q(min_guests__isnull=True) |
                Q(min_guests__lte=guest_count)
            ).filter(
                Q(max_guests__isnull=True) |
                Q(max_guests__gte=minimum_required_capacity)
            )

        except ValueError:

            guest_count = None

    else:

        guest_count = None


    # -----------------------------------------------------
    # BUDGET
    # -----------------------------------------------------

    if budget:

        try:

            budget_amount = float(budget)

            listings = listings.filter(
                base_price__lte=budget_amount
            )

        except ValueError:

            budget_amount = None

    else:

        budget_amount = None


    # -----------------------------------------------------
    # DATE
    # -----------------------------------------------------

    selected_date = None

    if event_date:

        try:

            selected_date = datetime.strptime(
                event_date,
                "%Y-%m-%d"
            ).date()

        except ValueError:

            selected_date = None


    if selected_date:

        # Available period
        listings = listings.filter(
            availability_periods__is_active=True,
            availability_periods__available_from__lte=selected_date,
            availability_periods__available_until__gte=selected_date,
        )

        # Blocked date remove
        listings = listings.exclude(
            blocked_dates__date=selected_date
        )

        # Confirmed booking remove
        listings = listings.exclude(
            bookings__status="confirmed",
            bookings__group__event_start_date__lte=selected_date,
            bookings__group__event_end_date__gte=selected_date,
        )


    listings = listings.distinct()


    # =====================================================
    # PACKAGES
    # =====================================================

    packages = (
        Package.objects
        .filter(is_active=True)
        .select_related(
            "vendor",
            "vendor__state",
            "vendor__city",
        )
        .prefetch_related(
            "package_categories__category",
            "package_categories__services",
            "gallery_images",
        )
    )


    # -----------------------------------------------------
    # PACKAGE LOCATION
    # -----------------------------------------------------

    if state_id:

        packages = packages.filter(
            vendor__state_id=state_id
        )


    if city_id:

        packages = packages.filter(
            vendor__city_id=city_id
        )

    # -----------------------------------------------------
    # PACKAGE GUEST CAPACITY
    # -----------------------------------------------------

    if guest_count is not None:

        minimum_required_capacity = max(
            guest_count - 50,
            0
        )

        packages = packages.filter(
            Q(min_guests__isnull=True) |
            Q(min_guests__lte=guest_count)
        ).filter(
            Q(max_guests__isnull=True) |
            Q(max_guests__gte=minimum_required_capacity)
        )

    # -----------------------------------------------------
    # PACKAGE BUDGET
    # -----------------------------------------------------

    if budget_amount is not None:

        packages = packages.filter(
            price__lte=budget_amount
        )


    # -----------------------------------------------------
    # PACKAGE CATEGORIES
    # -----------------------------------------------------

    if category_slugs:

        packages = packages.filter(
            package_categories__category__slug__in=category_slugs
        )


    packages = packages.distinct()


    # =====================================================
    # RESULTS
    # =====================================================

    return render(
        request,
        "listings/budget_results.html",
        {
            "listings": listings,
            "packages": packages,

            "guest_count": guest_count,
            "budget_amount": budget_amount,
            "selected_date": selected_date,

            "category_slugs": category_slugs,

            "selected_state_id": state_id,
            "selected_city_id": city_id,
        }
    )

    # -----------------------------------------------------
    # GET PARAMETERS
    # -----------------------------------------------------

    state_id = request.GET.get(
        "state",
        ""
    ).strip()

    city_id = request.GET.get(
        "city",
        ""
    ).strip()

    guests = request.GET.get(
        "guests",
        ""
    ).strip()

    budget = request.GET.get(
        "budget",
        ""
    ).strip()

    event_date = request.GET.get(
        "date",
        ""
    ).strip()

    category_slugs = request.GET.getlist(
        "category"
    )


    # =====================================================
    # LISTINGS
    # =====================================================

    listings = (
        Listing.objects
        .filter(
            is_active=True
        )
        .select_related(
            "vendor",
            "vendor__state",
            "vendor__city",
            "category",
            "state",
            "city",
        )
        .prefetch_related(
            "images",
            "services",
            "attribute_values__attribute",
        )
    )


    # -----------------------------------------------------
    # LOCATION
    # -----------------------------------------------------

    if state_id:

        listings = listings.filter(
            state_id=state_id
        )


    if city_id:

        listings = listings.filter(
            city_id=city_id
        )


    # -----------------------------------------------------
    # CATEGORY
    # -----------------------------------------------------

    if category_slugs:

        listings = listings.filter(
            category__slug__in=category_slugs
        )


    # -----------------------------------------------------
    # GUEST CAPACITY
    # -----------------------------------------------------

    guest_count = None

    if guests:

        try:

            guest_count = int(
                guests
            )

            listings = (
                listings
                .filter(
                    Q(min_guests__isnull=True) |
                    Q(
                        min_guests__lte=
                        guest_count
                    )
                )
                .filter(
                    Q(max_guests__isnull=True) |
                    Q(
                        max_guests__gte=
                        guest_count
                    )
                )
            )

        except ValueError:

            guest_count = None


    # -----------------------------------------------------
    # BUDGET
    # -----------------------------------------------------

    budget_amount = None

    if budget:

        try:

            budget_amount = float(
                budget
            )

            listings = listings.filter(
                base_price__lte=
                budget_amount
            )

        except ValueError:

            budget_amount = None


    # -----------------------------------------------------
    # DATE
    # -----------------------------------------------------

    selected_date = None

    if event_date:

        try:

            selected_date = datetime.strptime(
                event_date,
                "%Y-%m-%d"
            ).date()

        except ValueError:

            selected_date = None


    # -----------------------------------------------------
    # LISTING AVAILABILITY
    # -----------------------------------------------------

    if selected_date:

        # Listing must have an active
        # availability period containing the date.

        listings = listings.filter(
            availability_periods__is_active=True,
            availability_periods__available_from__lte=
                selected_date,
            availability_periods__available_until__gte=
                selected_date,
        )


        # Remove blocked listings.

        listings = listings.exclude(
            blocked_dates__date=
                selected_date
        )


        # Remove listings having a confirmed
        # booking on the selected date.

        listings = listings.exclude(
            bookings__status="confirmed",
            bookings__group__event_start_date__lte=
                selected_date,
            bookings__group__event_end_date__gte=
                selected_date,
        )


    listings = listings.distinct()


    # =====================================================
    # PACKAGES
    # =====================================================

    packages = (
        Package.objects
        .filter(
            is_active=True
        )
        .select_related(
            "vendor",
            "vendor__state",
            "vendor__city",
        )
        .prefetch_related(
            "listings__category",
            "listings__images",
            "listings__services",
        )
    )


    # -----------------------------------------------------
    # PACKAGE LOCATION
    # -----------------------------------------------------

    if state_id:

        packages = packages.filter(
            vendor__state_id=
                state_id
        )


    if city_id:

        packages = packages.filter(
            vendor__city_id=
                city_id
        )


    # -----------------------------------------------------
    # PACKAGE BUDGET
    # -----------------------------------------------------
    #
    # Package model has `price`, NOT `package_price`.
    #

    if budget_amount is not None:

        packages = packages.filter(
            price__lte=
                budget_amount
        )


    # -----------------------------------------------------
    # PACKAGE CATEGORY MATCHING
    # -----------------------------------------------------
    #
    # A package should contain ALL selected categories.
    #
    # Example:
    #
    # Selected:
    # Venue + DJ + Catering
    #
    # Package A:
    # Venue + DJ + Catering
    # -> SHOW
    #
    # Package B:
    # Venue + DJ
    # -> DON'T SHOW
    #

    for category_slug in category_slugs:

        packages = packages.filter(
            listings__category__slug=
                category_slug
        )


    packages = packages.distinct()


    # =====================================================
    # SELECTED STATE / CITY
    # =====================================================

    selected_state = None
    selected_city = None


    if state_id:

        try:

            if state_id:

                selected_state = (
                    State.objects
                    .filter(
                        id=state_id,
                        is_active=True
                    )
                    .first()
                )

        except Exception:

            selected_state = None


    if city_id:

        selected_city = (
            City.objects
            .filter(
                id=city_id,
                state_id=state_id,
                is_active=True
            )
            .first()
        )


    # =====================================================
    # RENDER
    # =====================================================

    return render(
        request,
        "listings/budget_results.html",
        {

            # Results
            "listings": listings,
            "packages": packages,

            # Planner values
            "guest_count": guest_count,
            "budget_amount": budget_amount,
            "selected_date": selected_date,
            "category_slugs": category_slugs,

            # Location
            "selected_state_id": state_id,
            "selected_city_id": city_id,

            "selected_state": selected_state,
            "selected_city": selected_city,

        }
    )

    state_id = request.GET.get("state", "").strip()
    city_id = request.GET.get("city", "").strip()
    guests = request.GET.get("guests", "").strip()
    budget = request.GET.get("budget", "").strip()
    event_date = request.GET.get("date", "").strip()

    category_slugs = request.GET.getlist("category")


    listings = (
        Listing.objects
        .filter(is_active=True)
        .select_related(
            "vendor",
            "vendor__state",
            "vendor__city",
            "category",
        )
        .prefetch_related(
            "images",
            "services",
        )
    )


    # -----------------------------------------------------
    # LOCATION
    # -----------------------------------------------------

    if state_id:
        listings = listings.filter(
            state_id=state_id
        )

    if city_id:
        listings = listings.filter(
            city_id=city_id
        )


    # -----------------------------------------------------
    # CATEGORIES
    # -----------------------------------------------------

    if category_slugs:

        listings = listings.filter(
            category__slug__in=category_slugs
        )


    # -----------------------------------------------------
    # GUEST CAPACITY
    # -----------------------------------------------------

    if guests:

        try:
            guest_count = int(guests)

            listings = listings.filter(
                Q(min_guests__isnull=True) |
                Q(min_guests__lte=guest_count)
            ).filter(
                Q(max_guests__isnull=True) |
                Q(max_guests__gte=guest_count)
            )

        except ValueError:
            guest_count = None

    else:
        guest_count = None


    # -----------------------------------------------------
    # BUDGET
    # -----------------------------------------------------

    if budget:

        try:
            budget_amount = float(budget)

            listings = listings.filter(
                base_price__lte=budget_amount
            )

        except ValueError:
            budget_amount = None

    else:
        budget_amount = None


    # -----------------------------------------------------
    # DATE
    # -----------------------------------------------------

    selected_date = None

    if event_date:

        try:

            selected_date = datetime.strptime(
                event_date,
                "%Y-%m-%d"
            ).date()

        except ValueError:

            selected_date = None


    if selected_date:

        # Vendor must have an availability period
        # containing the selected date.
        listings = listings.filter(
            availability_periods__is_active=True,
            availability_periods__available_from__lte=selected_date,
            availability_periods__available_until__gte=selected_date,
        )

        # Remove blocked listings for that date.
        listings = listings.exclude(
            blocked_dates__date=selected_date
        )

        # Remove already confirmed bookings.
        listings = listings.exclude(
            bookings__status="confirmed",
            bookings__group__event_start_date__lte=selected_date,
            bookings__group__event_end_date__gte=selected_date,
        )


    listings = listings.distinct()


    # -----------------------------------------------------
    # PACKAGES
    # -----------------------------------------------------

    packages = (
        Package.objects
        .filter(is_active=True)
        .select_related(
            "vendor",
            "vendor__state",
            "vendor__city",
        )
        .prefetch_related(
            "listings__category",
            "listings__images",
        )
    )


    if state_id:
        packages = packages.filter(
            vendor__state_id=state_id
        )


    if city_id:
        packages = packages.filter(
            vendor__city_id=city_id
        )


    if budget_amount is not None:

        packages = packages.filter(
            price__lte=budget_amount
        )


    if category_slugs:

        packages = packages.filter(
            listings__category__slug__in=category_slugs
        )


    packages = packages.distinct()


    return render(
        request,
        "listings/budget_results.html",
        {
            "listings": listings,
            "packages": packages,

            "guest_count": guest_count,
            "budget_amount": budget_amount,
            "selected_date": selected_date,

            "category_slugs": category_slugs,

            "selected_state_id": state_id,
            "selected_city_id": city_id,
        }
    )

# =========================================================
# VENDOR FILTER RESULTS
# =========================================================

# =========================================================
# FILTER RESULTS
# =========================================================

# =========================================================
# FILTER RESULTS
# =========================================================

def filter_results(request):

    # =====================================================
    # BASIC FILTERS
    # =====================================================

    city_id = request.GET.get(
        "city",
        ""
    ).strip()

    guests = request.GET.get(
        "guests",
        ""
    ).strip()

    min_price = request.GET.get(
        "min_price",
        ""
    ).strip()

    max_price = request.GET.get(
        "max_price",
        ""
    ).strip()

    pricing_type = request.GET.get(
        "pricing_type",
        ""
    ).strip()


    # =====================================================
    # CATEGORY / SERVICE
    # =====================================================

    category_slugs = request.GET.getlist(
        "category"
    )

    service_slugs = request.GET.getlist(
        "service"
    )


    # =====================================================
    # DYNAMIC ATTRIBUTE FILTERS
    # =====================================================

    attribute_filters = {}

    for key in request.GET:

        if not key.startswith("attribute_"):
            continue

        try:

            attribute_id = int(
                key.split("_", 1)[1]
            )

        except (
            ValueError,
            IndexError
        ):

            continue


        values = [
            value.strip()
            for value in request.GET.getlist(key)
            if value.strip()
        ]


        if values:

            attribute_filters[attribute_id] = values


    # =====================================================
    # GUEST RANGE
    # =====================================================

    guest_min = None
    guest_max = None


    if guests == "100":

        guest_max = 99

    elif guests == "250":

        guest_min = 100
        guest_max = 250

    elif guests == "500":

        guest_min = 250
        guest_max = 500

    elif guests == "1000":

        guest_min = 500
        guest_max = 1000

    elif guests == "1000+":

        guest_min = 1001


    # =====================================================
    # PRICE
    # =====================================================

    try:

        min_price_value = (
            float(min_price)
            if min_price
            else None
        )

    except ValueError:

        min_price_value = None


    try:

        max_price_value = (
            float(max_price)
            if max_price
            else None
        )

    except ValueError:

        max_price_value = None


    # =====================================================
    # LISTINGS
    # =====================================================

    listings = (
        Listing.objects
        .filter(
            is_active=True
        )
        .select_related(
            "vendor",
            "vendor__state",
            "vendor__city",
            "category",
            "state",
            "city",
        )
        .prefetch_related(
            "images",
            "videos",
            "services",
            "event_types",
            "attribute_values__attribute",
        )
    )


    # -----------------------------------------------------
    # CITY
    # -----------------------------------------------------

    if city_id:

        listings = listings.filter(
            city_id=city_id
        )


    # -----------------------------------------------------
    # GUESTS
    # -----------------------------------------------------

    if guest_min is not None:

        listings = listings.filter(
            Q(max_guests__isnull=True)
            |
            Q(max_guests__gte=guest_min)
        )


    if guest_max is not None:

        listings = listings.filter(
            Q(min_guests__isnull=True)
            |
            Q(min_guests__lte=guest_max)
        )


    # -----------------------------------------------------
    # PRICE
    # -----------------------------------------------------

    if min_price_value is not None:

        listings = listings.filter(
            base_price__gte=min_price_value
        )


    if max_price_value is not None:

        listings = listings.filter(
            base_price__lte=max_price_value
        )


    # -----------------------------------------------------
    # CATEGORY
    # -----------------------------------------------------

    if category_slugs:

        listings = listings.filter(
            category__slug__in=category_slugs
        )


    # -----------------------------------------------------
    # SERVICE
    # -----------------------------------------------------

    if service_slugs:

        listings = listings.filter(
            services__slug__in=service_slugs
        )


    # -----------------------------------------------------
    # DYNAMIC ATTRIBUTES
    # -----------------------------------------------------

    for attribute_id, values in attribute_filters.items():

        listings = listings.filter(
            attribute_values__attribute_id=attribute_id,
            attribute_values__value__in=values,
        )


    listings = listings.distinct()


    # =====================================================
    # PACKAGES
    # =====================================================

    packages = (
        Package.objects
        .filter(
            is_active=True
        )
        .select_related(
            "vendor",
            "vendor__state",
            "vendor__city",
        )
        .prefetch_related(
            "package_categories__category",
            "package_categories__services",
            "gallery_images",
        )
    )


    # -----------------------------------------------------
    # CITY
    # -----------------------------------------------------

    if city_id:

        packages = packages.filter(
            vendor__city_id=city_id
        )


    # -----------------------------------------------------
    # GUESTS
    # -----------------------------------------------------

    if guest_min is not None:

        packages = packages.filter(
            Q(max_guests__isnull=True)
            |
            Q(max_guests__gte=guest_min)
        )


    if guest_max is not None:

        packages = packages.filter(
            Q(min_guests__isnull=True)
            |
            Q(min_guests__lte=guest_max)
        )


    # -----------------------------------------------------
    # PRICE
    # -----------------------------------------------------

    if min_price_value is not None:

        packages = packages.filter(
            price__gte=min_price_value
        )


    if max_price_value is not None:

        packages = packages.filter(
            price__lte=max_price_value
        )


    # -----------------------------------------------------
    # CATEGORY
    # -----------------------------------------------------

    if category_slugs:

        for category_slug in category_slugs:

            packages = packages.filter(
                package_categories__category__slug=
                category_slug
            )


    # -----------------------------------------------------
    # SERVICE
    # -----------------------------------------------------

    if service_slugs:

        for service_slug in service_slugs:

            packages = packages.filter(
                package_categories__services__slug=
                service_slug
            )


    packages = packages.distinct()


    # =====================================================
    # FILTER DATA
    # =====================================================

    cities = (
        City.objects
        .filter(
            is_active=True
        )
        .order_by("name")
    )


    categories = (
        Category.objects
        .filter(
            is_active=True
        )
        .order_by("name")
    )


    # =====================================================
    # DYNAMIC ADMIN ATTRIBUTES
    # =====================================================

    filter_attributes = []

    for attribute in (
        CategoryAttribute.objects
        .order_by("order", "id")
    ):

        options = [
            option.strip()
            for option in (
                attribute.options or ""
            ).split(",")
            if option.strip()
        ]

        filter_attributes.append({
            "id": attribute.id,
            "label": attribute.label,
            "field_type": attribute.field_type,
            "options": options,
            "unit": attribute.unit,
        })


    # =====================================================
    # RESULT COUNT
    # =====================================================

    total_matches = (
        listings.count()
        +
        packages.count()
    )


    # =====================================================
    # RENDER
    # =====================================================

    return render(
        request,
        "listings/filter_results.html",
        {
            "listings":
                listings,

            "packages":
                packages,

            "cities":
                cities,

            "categories":
                categories,

            "filter_attributes":
                filter_attributes,

            "selected_city_id":
                city_id,

            "selected_guests":
                guests,

            "selected_min_price":
                min_price,

            "selected_max_price":
                max_price,

            "selected_pricing_type":
                pricing_type,

            "selected_categories":
                category_slugs,

            "selected_services":
                service_slugs,

            "selected_attribute_values":
                attribute_filters,

            "total_matches":
                total_matches,
        }
    )

    # =====================================================
    # BASIC FILTERS
    # =====================================================

    state_id = request.GET.get(
        "state",
        ""
    ).strip()

    city_id = request.GET.get(
        "city",
        ""
    ).strip()

    guests = request.GET.get(
        "guests",
        ""
    ).strip()

    min_price = request.GET.get(
        "min_price",
        ""
    ).strip()

    max_price = request.GET.get(
        "max_price",
        ""
    ).strip()

    pricing_type = request.GET.get(
        "pricing_type",
        ""
    ).strip()


    # =====================================================
    # CATEGORY / SERVICE
    # =====================================================

    category_slugs = request.GET.getlist(
        "category"
    )

    service_slugs = request.GET.getlist(
        "service"
    )


    # =====================================================
    # DYNAMIC ATTRIBUTE FILTERS
    #
    # Example:
    #
    # attribute_12=Vegetarian
    # attribute_15=5 Star
    #
    # Same attribute can have multiple values:
    #
    # attribute_12=Vegetarian
    # attribute_12=Vegan
    # =====================================================

    attribute_filters = {}

    for key in request.GET:

        if not key.startswith(
            "attribute_"
        ):
            continue

        try:

            attribute_id = int(
                key.split(
                    "_",
                    1
                )[1]
            )

        except (
            ValueError,
            IndexError
        ):

            continue


        values = [
            value.strip()
            for value in request.GET.getlist(key)
            if value.strip()
        ]


        if values:

            attribute_filters[
                attribute_id
            ] = values


    # =====================================================
    # GUEST RANGE
    # =====================================================

    guest_min = None
    guest_max = None


    if guests:

        if guests == "100":

            guest_max = 99

        elif guests == "250":

            guest_min = 100
            guest_max = 250

        elif guests == "500":

            guest_min = 250
            guest_max = 500

        elif guests == "1000":

            guest_min = 500
            guest_max = 1000

        elif guests == "1000+":

            guest_min = 1001


    # =====================================================
    # PRICE
    # =====================================================

    try:

        min_price_value = (
            float(min_price)
            if min_price
            else None
        )

    except ValueError:

        min_price_value = None


    try:

        max_price_value = (
            float(max_price)
            if max_price
            else None
        )

    except ValueError:

        max_price_value = None


    # =====================================================
    # LISTINGS
    # =====================================================

    listings = (
        Listing.objects
        .filter(
            is_active=True
        )
        .select_related(
            "vendor",
            "vendor__state",
            "vendor__city",
            "category",
            "state",
            "city",
        )
        .prefetch_related(
            "images",
            "videos",
            "services",
            "event_types",
            "attribute_values__attribute",
        )
    )


    # =====================================================
    # LOCATION
    # =====================================================

    if state_id:

        listings = listings.filter(
            state_id=state_id
        )


    if city_id:

        listings = listings.filter(
            city_id=city_id
        )


    # =====================================================
    # GUEST CAPACITY
    # =====================================================

    if guest_min is not None:

        listings = listings.filter(
            Q(max_guests__isnull=True)
            |
            Q(max_guests__gte=guest_min)
        )


    if guest_max is not None:

        listings = listings.filter(
            Q(min_guests__isnull=True)
            |
            Q(min_guests__lte=guest_max)
        )


    # =====================================================
    # PRICE
    # =====================================================

    if min_price_value is not None:

        listings = listings.filter(
            base_price__gte=min_price_value
        )


    if max_price_value is not None:

        listings = listings.filter(
            base_price__lte=max_price_value
        )


    # =====================================================
    # CATEGORY
    # =====================================================

    if category_slugs:

        listings = listings.filter(
            category__slug__in=category_slugs
        )


    # =====================================================
    # SERVICE
    # =====================================================

    if service_slugs:

        listings = listings.filter(
            services__slug__in=service_slugs
        )


    # =====================================================
    # DYNAMIC ATTRIBUTES
    #
    # Every selected attribute must match.
    #
    # Example:
    #
    # Food = Vegetarian
    # Venue Type = Resort
    #
    # BOTH conditions must be satisfied.
    # =====================================================

    for attribute_id, values in attribute_filters.items():

        listings = listings.filter(
            attribute_values__attribute_id=attribute_id,
            attribute_values__value__in=values,
        )


    listings = listings.distinct()


    # =====================================================
    # PACKAGES
    # =====================================================

    packages = (
        Package.objects
        .filter(
            is_active=True
        )
        .select_related(
            "vendor",
            "vendor__state",
            "vendor__city",
        )
        .prefetch_related(
            "package_categories__category",
            "package_categories__services",
            "gallery_images",
        )
    )


    # =====================================================
    # PACKAGE LOCATION
    # =====================================================

    if state_id:

        packages = packages.filter(
            vendor__state_id=state_id
        )


    if city_id:

        packages = packages.filter(
            vendor__city_id=city_id
        )


    # =====================================================
    # PACKAGE GUEST CAPACITY
    # =====================================================

    if guest_min is not None:

        packages = packages.filter(
            Q(max_guests__isnull=True)
            |
            Q(max_guests__gte=guest_min)
        )


    if guest_max is not None:

        packages = packages.filter(
            Q(min_guests__isnull=True)
            |
            Q(min_guests__lte=guest_max)
        )


    # =====================================================
    # PACKAGE PRICE
    # =====================================================

    if min_price_value is not None:

        packages = packages.filter(
            price__gte=min_price_value
        )


    if max_price_value is not None:

        packages = packages.filter(
            price__lte=max_price_value
        )


    # =====================================================
    # PACKAGE CATEGORY
    # =====================================================

    if category_slugs:

        for category_slug in category_slugs:

            packages = packages.filter(
                package_categories__category__slug=
                category_slug
            )


    # =====================================================
    # PACKAGE SERVICE
    # =====================================================

    if service_slugs:

        for service_slug in service_slugs:

            packages = packages.filter(
                package_categories__services__slug=
                service_slug
            )


    # =====================================================
    # NOTE
    #
    # Packages currently have their own independent
    # architecture and are NOT connected to Listing.
    #
    # Therefore ListingAttributeValue filters cannot
    # automatically be applied to Package.
    #
    # Package attributes should be added separately
    # when Package dynamic attributes are implemented.
    # =====================================================

    packages = packages.distinct()


    # =====================================================
    # FILTER DATA
    # =====================================================

    states = (
        State.objects
        .filter(
            is_active=True
        )
        .order_by("name")
    )


    cities = (
        City.objects
        .filter(
            is_active=True
        )
        .order_by("name")
    )


    # =====================================================
    # FILTER ATTRIBUTES
    #
    # Admin-created attributes.
    # =====================================================

    filter_attributes = []

    for attribute in (
        CategoryAttribute.objects
        .order_by("order", "id")
    ):

        options = [
            option.strip()
            for option in (
                attribute.options or ""
            ).split(",")
            if option.strip()
        ]

        filter_attributes.append({
            "id": attribute.id,
            "label": attribute.label,
            "field_type": attribute.field_type,
            "options": options,
            "unit": attribute.unit,
        })


    # =====================================================
    # SELECTED VALUES
    # =====================================================

    selected_attribute_values = {}

    for attribute_id, values in attribute_filters.items():

        selected_attribute_values[
            str(attribute_id)
        ] = values


    # =====================================================
    # RESULT COUNT
    # =====================================================

    total_matches = (
        listings.count()
        +
        packages.count()
    )


    # =====================================================
    # RENDER
    # =====================================================

    return render(
        request,
        "listings/filter_results.html",
        {
            "listings":
                listings,

            "packages":
                packages,

            "states":
                states,

            "cities":
                cities,

            "filter_attributes":
                filter_attributes,

            "selected_state_id":
                state_id,

            "selected_city_id":
                city_id,

            "selected_guests":
                guests,

            "selected_min_price":
                min_price,

            "selected_max_price":
                max_price,

            "selected_pricing_type":
                pricing_type,

            "selected_categories":
                category_slugs,

            "selected_services":
                service_slugs,

            "selected_attribute_values":
                selected_attribute_values,

            "total_matches":
                total_matches,
        }
    )

    # =====================================================
    # GET PARAMETERS
    # =====================================================

    state_id = request.GET.get(
        "state",
        ""
    ).strip()

    city_id = request.GET.get(
        "city",
        ""
    ).strip()

    guests = request.GET.get(
        "guests",
        ""
    ).strip()

    min_price = request.GET.get(
        "min_price",
        ""
    ).strip()

    max_price = request.GET.get(
        "max_price",
        ""
    ).strip()

    pricing_type = request.GET.get(
        "pricing_type",
        ""
    ).strip()

    category_slugs = request.GET.getlist(
        "category"
    )

    service_slugs = request.GET.getlist(
        "service"
    )


    # =====================================================
    # GUEST RANGE
    # =====================================================

    guest_min = None
    guest_max = None

    if guests:

        if guests == "100":

            guest_max = 99

        elif guests == "250":

            guest_min = 100
            guest_max = 250

        elif guests == "500":

            guest_min = 250
            guest_max = 500

        elif guests == "1000":

            guest_min = 500
            guest_max = 1000

        elif guests == "1000+":

            guest_min = 1001


    # =====================================================
    # PRICE
    # =====================================================

    try:

        min_price_value = (
            float(min_price)
            if min_price
            else None
        )

    except ValueError:

        min_price_value = None


    try:

        max_price_value = (
            float(max_price)
            if max_price
            else None
        )

    except ValueError:

        max_price_value = None


    # =====================================================
    # LISTINGS
    # =====================================================

    listings = (
        Listing.objects
        .filter(
            is_active=True
        )
        .select_related(
            "vendor",
            "vendor__state",
            "vendor__city",
            "category",
            "state",
            "city",
        )
        .prefetch_related(
            "images",
            "videos",
            "services",
            "event_types",
            "attribute_values__attribute",
        )
    )


    # =====================================================
    # CITY
    # =====================================================

    if state_id:

        listings = listings.filter(
            state_id=state_id
        )


    if city_id:

        listings = listings.filter(
            city_id=city_id
        )


    # =====================================================
    # GUEST CAPACITY
    # =====================================================

    if guest_min is not None:

        listings = listings.filter(
            Q(max_guests__isnull=True)
            |
            Q(max_guests__gte=guest_min)
        )


    if guest_max is not None:

        listings = listings.filter(
            Q(min_guests__isnull=True)
            |
            Q(min_guests__lte=guest_max)
        )


    # =====================================================
    # PRICE
    # =====================================================

    if min_price_value is not None:

        listings = listings.filter(
            base_price__gte=min_price_value
        )


    if max_price_value is not None:

        listings = listings.filter(
            base_price__lte=max_price_value
        )


    # =====================================================
    # CATEGORY
    # =====================================================

    if category_slugs:

        listings = listings.filter(
            category__slug__in=category_slugs
        )


    # =====================================================
    # SERVICES
    # =====================================================

    if service_slugs:

        listings = listings.filter(
            services__slug__in=service_slugs
        )


    listings = listings.distinct()


    # =====================================================
    # PACKAGES
    # =====================================================

    packages = (
        Package.objects
        .filter(
            is_active=True
        )
        .select_related(
            "vendor",
            "vendor__state",
            "vendor__city",
        )
        .prefetch_related(
            "package_categories__category",
            "package_categories__services",
            "gallery_images",
        )
    )


    # =====================================================
    # PACKAGE CITY
    # =====================================================

    if state_id:

        packages = packages.filter(
            vendor__state_id=state_id
        )


    if city_id:

        packages = packages.filter(
            vendor__city_id=city_id
        )


    # =====================================================
    # PACKAGE GUEST CAPACITY
    # =====================================================

    if guest_min is not None:

        packages = packages.filter(
            Q(max_guests__isnull=True)
            |
            Q(max_guests__gte=guest_min)
        )


    if guest_max is not None:

        packages = packages.filter(
            Q(min_guests__isnull=True)
            |
            Q(min_guests__lte=guest_max)
        )


    # =====================================================
    # PACKAGE PRICE
    # =====================================================

    if min_price_value is not None:

        packages = packages.filter(
            price__gte=min_price_value
        )


    if max_price_value is not None:

        packages = packages.filter(
            price__lte=max_price_value
        )


    # =====================================================
    # PACKAGE CATEGORY
    # =====================================================

    if category_slugs:

        for category_slug in category_slugs:

            packages = packages.filter(
                package_categories__category__slug=
                category_slug
            )


    # =====================================================
    # PACKAGE SERVICE
    # =====================================================

    if service_slugs:

        for service_slug in service_slugs:

            packages = packages.filter(
                package_categories__services__slug=
                service_slug
            )


    packages = packages.distinct()


    # =====================================================
    # CITIES
    # =====================================================

    cities = (
        City.objects
        .filter(
            is_active=True
        )
        .order_by("name")
    )


    # =====================================================
    # SELECTED CITY
    # =====================================================

    selected_city = None

    if city_id:

        selected_city = (
            City.objects
            .filter(
                id=city_id,
                is_active=True
            )
            .first()
        )


    # =====================================================
    # RESULT COUNT
    # =====================================================

    total_matches = (
        listings.count()
        +
        packages.count()
    )


    # =====================================================
    # RENDER
    # =====================================================

    return render(
        request,
        "listings/filter_results.html",
        {
            "listings": listings,
            "packages": packages,

            "cities": cities,

            "selected_city": selected_city,
            "selected_city_id": city_id,

            "selected_state_id": state_id,

            "guests": guests,

            "min_price": min_price,
            "max_price": max_price,

            "pricing_type": pricing_type,

            "category_slugs":
                category_slugs,

            "service_slugs":
                service_slugs,

            "total_matches":
                total_matches,
        }
    )