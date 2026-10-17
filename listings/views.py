from datetime import date, timedelta, datetime

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse
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

from django.views.decorators.http import require_POST

# =========================================================
# ATTRIBUTE FILTER HELPER (supports multiselect values)
# =========================================================

def _filter_by_attribute(queryset, attribute_id, values):
    """Filter listings by one attribute.
    Multiselect values are stored as "A, B, C", so they need
    delimiter-aware matching; other types use exact match."""

    field_type = (
        CategoryAttribute.objects
        .filter(pk=attribute_id)
        .values_list('field_type', flat=True)
        .first()
    )

    if field_type != 'multiselect':
        return queryset.filter(
            attribute_values__attribute_id=attribute_id,
            attribute_values__value__in=values,
        )

    condition = Q()

    for value in values:
        condition |= (
            Q(attribute_values__value__iexact=value)
            | Q(attribute_values__value__istartswith=f'{value}, ')
            | Q(attribute_values__value__iendswith=f', {value}')
            | Q(attribute_values__value__icontains=f', {value}, ')
        )

    return queryset.filter(
        condition,
        attribute_values__attribute_id=attribute_id,
    )

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
            'service',
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

                        _ensure_not_past(
                            _parse_date(available_from, 'Available from'),
                            'Available from date'
                        )
                        _ensure_not_past(
                            _parse_date(available_until, 'Available until'),
                            'Available until date'
                        )

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



# =========================================================
# DATE HELPERS (availability / blocked ranges)
# =========================================================

MAX_BLOCKED_RANGE_DAYS = 366


def _parse_date(value, label):
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except (TypeError, ValueError):
        raise ValidationError(f'{label}: please enter a valid date.')


def _ensure_not_past(day, label):
    if day < date.today():
        raise ValidationError(f'{label} cannot be in the past.')


def _date_range(start, end):
    """All dates from start to end (inclusive)."""

    if end < start:
        raise ValidationError(
            'Blocked "until" date cannot be before the "from" date.'
        )

    total_days = (end - start).days + 1

    if total_days > MAX_BLOCKED_RANGE_DAYS:
        raise ValidationError(
            f'You can block at most {MAX_BLOCKED_RANGE_DAYS} days at a time.'
        )

    return [start + timedelta(days=i) for i in range(total_days)]


def get_blocked_ranges(listing):
    """Group consecutive blocked days having the same reason
    into ranges, e.g. 3 Nov -> 5 Nov (Maintenance)."""

    ranges = []

    for blocked in listing.blocked_dates.order_by('date'):

        last = ranges[-1] if ranges else None

        if (
            last
            and last['reason'] == blocked.reason
            and (blocked.date - last['end']) == timedelta(days=1)
        ):
            last['end'] = blocked.date
            last['ids'].append(blocked.id)

        else:
            ranges.append({
                'start': blocked.date,
                'end': blocked.date,
                'reason': blocked.reason,
                'ids': [blocked.id],
            })

    for item in ranges:
        item['key'] = item['ids'][0]
        item['ids_csv'] = ','.join(str(i) for i in item['ids'])

    return ranges


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

        # Only dates the vendor actually changed must not be in the past
        if date_from != period.available_from.isoformat():
            _ensure_not_past(
                _parse_date(date_from, 'Available from'),
                'Available from date'
            )

        if date_until != period.available_until.isoformat():
            _ensure_not_past(
                _parse_date(date_until, 'Available until'),
                'Available until date'
            )

        period.available_from = date_from
        period.available_until = date_until
        period.is_active = (
            f'availability_active_{pid}' in request.POST
        )

        period.full_clean()
        period.save()


def update_existing_blocked_dates(request, listing):
    """Each existing blocked RANGE (from - until + reason) is edited
    as one unit; its day rows are rebuilt."""

    for item in get_blocked_ranges(listing):

        key = item['key']

        new_from = request.POST.get(f'blocked_from_{key}')
        new_until = request.POST.get(f'blocked_until_{key}')

        # range not present in the submitted form
        if new_from is None or new_until is None:
            continue

        new_from = new_from.strip()
        new_until = new_until.strip()

        if not (new_from and new_until):
            raise ValidationError('Blocked dates cannot be empty.')

        reason = request.POST.get(
            f'blocked_reason_{key}', ''
        ).strip()

        start = _parse_date(new_from, 'Blocked from')
        end = _parse_date(new_until, 'Blocked until')

        if (
            start == item['start']
            and end == item['end']
            and reason == item['reason']
        ):
            continue

        if start != item['start']:
            _ensure_not_past(start, 'Blocked from date')

        days = _date_range(start, end)

        listing.blocked_dates.filter(id__in=item['ids']).delete()

        for day in days:
            ListingBlockedDate.objects.update_or_create(
                listing=listing,
                date=day,
                defaults={'reason': reason}
            )


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

                        # One availability period per listing:
                        # vendor must edit the existing dates.
                        if listing.availability_periods.exists():
                            raise ValidationError(
                                'This listing already has an availability '
                                'period. Please edit the existing dates '
                                'instead of adding a new one.'
                            )

                        if not (available_from and available_until):
                            raise ValidationError(
                                'Please select both Available From '
                                'and Available Until dates.'
                            )

                        _ensure_not_past(
                            _parse_date(available_from, 'Available from'),
                            'Available from date'
                        )
                        _ensure_not_past(
                            _parse_date(available_until, 'Available until'),
                            'Available until date'
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

                    # ---------- NEW BLOCKED DATE RANGE ----------
                    new_from = request.POST.get(
                        'new_blocked_from', ''
                    ).strip()
                    new_until = request.POST.get(
                        'new_blocked_until', ''
                    ).strip()

                    if new_from or new_until:

                        if not new_from:
                            raise ValidationError(
                                'Please select the blocked "From" date.'
                            )

                        # only "from" given -> single day
                        start = _parse_date(new_from, 'Blocked from')
                        end = _parse_date(
                            new_until or new_from, 'Blocked until'
                        )

                        _ensure_not_past(start, 'Blocked from date')

                        blocked_reason = request.POST.get(
                            'blocked_date_reason', ''
                        ).strip()

                        for day in _date_range(start, end):
                            ListingBlockedDate.objects.get_or_create(
                                listing=listing,
                                date=day,
                                defaults={'reason': blocked_reason}
                            )

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
            'blocked_ranges': get_blocked_ranges(listing),
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
            'service'
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

        # A blocked RANGE is stored as one row per day; the form sends
        # all ids of the range in range_ids.
        ids = {blocked_date.id}

        for raw_id in request.POST.get('range_ids', '').split(','):
            if raw_id.strip().isdigit():
                ids.add(int(raw_id))

        ListingBlockedDate.objects.filter(
            id__in=ids,
            listing=blocked_date.listing
        ).delete()

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
            'service',
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




    # -----------------------------------------------------
    # RESOLVE SELECTED CITY
    # -----------------------------------------------------

    selected_city = None

    # Explicit city parameter has priority.
    # Used by Popular Cities links and other city filters.
    if city:
        active_cities = City.objects.filter(
            is_active=True,
            state__is_active=True,
        )

        if city.isdigit():
            selected_city = active_cities.filter(
                pk=city
            ).first()
        else:
            selected_city = active_cities.filter(
                name__iexact=city
            ).first()

        if selected_city:
            request.session["selected_city_id"] = selected_city.id
            city = str(selected_city.id)

    # If no explicit city was passed, check whether
    # the entire search text exactly matches a city.
    elif query:
        typed_city = City.objects.filter(
            name__iexact=query,
            is_active=True,
            state__is_active=True,
        ).first()

        if typed_city:
            selected_city = typed_city
            request.session["selected_city_id"] = typed_city.id

            # Searching only for a city means show its listings,
            # not listings whose titles contain the city name.
            city = str(typed_city.id)
            query = ""

    # Otherwise use the city already stored in the session.
    if selected_city is None and request.selected_city:
        selected_city = request.selected_city

    if selected_city:
        city = str(selected_city.id)
        listings = listings.filter(
            city_id=selected_city.id
        )



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
                service__name__icontains=query
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

    if selected_city:
        listings = listings.filter(
            Q(city_id=selected_city.id)
            | Q(vendor__city_id=selected_city.id)
        )


    # =====================================================
    # SERVICE
    # =====================================================

    if service_slug:

        listings = listings.filter(
            service__slug=service_slug
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

        listings = _filter_by_attribute(listings, attribute_id, values)


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

            'selected_city_id': city,

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
    """Attributes of ONE selected service (add / edit listing form)."""

    category_id = request.GET.get('category_id')
    service_id = request.GET.get('service_id')

    if not category_id or not service_id:
        return JsonResponse({'attributes': []})

    try:
        category_id = int(category_id)
        service_id = int(service_id)
    except ValueError:
        return JsonResponse({'attributes': []})

    attributes = (
        CategoryAttribute.objects
        .filter(
            category_id=category_id,
            service_id=service_id,
            service__category_id=category_id,
        )
        .order_by('order', 'id')
    )

    data = []

    for attribute in attributes:
        options = [
            option.strip()
            for option in (attribute.options or '').split(',')
            if option.strip()
        ]

        data.append({
            'id': attribute.id,
            'label': attribute.label,
            'field_type': attribute.field_type,
            'options': options,
            'unit': attribute.unit,
            'help_text': attribute.help_text,
            'is_required': attribute.is_required,
        })

    return JsonResponse({'attributes': data})

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


    
    if city_id:
        selected = City.objects.filter(
            pk=city_id,
            is_active=True,
            state__is_active=True,
        ).first()

        if selected:
            request.session["selected_city_id"] = selected.id
            city_id = str(selected.id)
        else:
            city_id = ""
            selected = request.selected_city
    else:
        selected = request.selected_city
        if selected:
            city_id = str(selected.id)



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
            "service",
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
            service__slug__in=service_slugs
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

        listings = _filter_by_attribute(listings, attribute_id, values)

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





@require_POST
def select_city(request):
    city_id = request.POST.get("city_id", "").strip()

    if not city_id:
        request.session.pop("selected_city_id", None)
        return JsonResponse({"success": True, "city": None})

    city = City.objects.filter(
        id=city_id,
        is_active=True,
        state__is_active=True,
    ).first()

    if city is None:
        return JsonResponse(
            {"success": False, "message": "Please select a valid city."},
            status=400,
        )

    request.session["selected_city_id"] = city.id

    return JsonResponse({
        "success": True,
        "city": city.name,
        "city_id": city.id,
    })








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

def save_listing_attributes(listing, form):
    """Save attribute values of the listing's ONE service and sync
    min_guests / max_guests from the special attributes."""

    if listing.service_id:
        attributes = list(
            CategoryAttribute.objects
            .filter(
                category=listing.category,
                service_id=listing.service_id
            )
            .order_by('order', 'id')
        )
    else:
        attributes = []

    # Values of attributes that do not belong to the (new) service
    ListingAttributeValue.objects.filter(
        listing=listing
    ).exclude(
        attribute_id__in=[a.id for a in attributes]
    ).delete()

    for attribute in attributes:

        value = form.cleaned_data.get(f'attribute_{attribute.id}')

        if value is None or value == '' or value == []:
            ListingAttributeValue.objects.filter(
                listing=listing,
                attribute=attribute
            ).delete()
            continue

        if attribute.field_type == 'boolean':
            value = 'true' if value == 'true' else 'false'

        elif attribute.field_type == 'multiselect':
            value = ', '.join(value)

        else:
            value = str(value)

        ListingAttributeValue.objects.update_or_create(
            listing=listing,
            attribute=attribute,
            defaults={'value': value}
        )

    # Guest capacity columns (used by search / budget planner)
    special = form.get_special_values()

    Listing.objects.filter(pk=listing.pk).update(
        min_guests=special['min_guests'],
        max_guests=special['max_guests'],
    )

# =========================================================
# BUDGET PLANNER RESULTS
# =========================================================

def budget_results(request):

    
    state_id = request.GET.get("state", "").strip()
    city_id = request.GET.get("city", "").strip()

    if city_id:
        selected = City.objects.filter(
            pk=city_id,
            is_active=True,
            state__is_active=True,
        ).first()

        if selected:
            request.session["selected_city_id"] = selected.id
            city_id = str(selected.id)
            state_id = str(selected.state_id)
        else:
            city_id = ""
            selected = request.selected_city
            if selected:
                city_id = str(selected.id)
                state_id = str(selected.state_id)

    elif request.selected_city:
        selected = request.selected_city
        city_id = str(selected.id)
        state_id = str(selected.state_id)

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
            "service",
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

        
    city_id = request.GET.get("city", "").strip()
    
    if city_id:
        selected = City.objects.filter(
            pk=city_id,
            is_active=True,
            state__is_active=True,
        ).first()
    
        if selected:
            request.session["selected_city_id"] = selected.id
            city_id = str(selected.id)
        else:
            city_id = ""
            if request.selected_city:
                city_id = str(request.selected_city.id)
    
    elif request.selected_city:
        city_id = str(request.selected_city.id)
    

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
            "service",
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
            service__slug__in=service_slugs
        )


    # -----------------------------------------------------
    # DYNAMIC ATTRIBUTES
    # -----------------------------------------------------

    for attribute_id, values in attribute_filters.items():

        listings = _filter_by_attribute(listings, attribute_id, values)


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
