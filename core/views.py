from django.shortcuts import render
from django.db.models import Count, Prefetch, Q

from categories.models import Category, Service
from core.context_processors import selected_city
from core.models import EventType
from listings.models import Listing
from packages.models import Package
from vendors.models import VendorProfile
from locations.models import City,State


def home(request):


    selected_city = request.selected_city
    # =========================================================
    # CATEGORIES
    # =========================================================

    categories = (
        Category.objects
        .filter(is_active=True)
        .annotate(
            vendor_count=Count(
                'listings__vendor',
                distinct=True
            )
        )
    )


    # =========================================================
    # EVENT TYPES
    # =========================================================

    event_types = (
        EventType.objects
        .filter(is_active=True)
        .order_by('name')
    )


    #active listings
    active_listings = (
        Listing.objects
        .filter(is_active=True)
        .select_related(
            "category",
            "service",
            "state",
            "city",
        )
        .prefetch_related(
            "attribute_values__attribute",
        )
    )

    
    # Selected city filter
    if selected_city:
        active_listings = active_listings.filter(
            city_id=selected_city.id
        )




    # =========================================================
    # FEATURED VENDORS
    # =========================================================

    featured_vendors = (
        VendorProfile.objects

        .filter(
            is_featured=True,
            listings__is_active=True,
            **({"city_id": selected_city.id} if selected_city else {}),
        )

        .distinct()
        .order_by(
            "featured_order",
            "business_name",
        )
        .prefetch_related(
            Prefetch(
                "listings",
                queryset=active_listings,
                to_attr="active_listings",
            )
        )[:6]
    )



    # =========================================================
    # FEATURED PACKAGES
    # =========================================================


    featured_packages = (
        Package.objects
        .filter(
            is_active=True,
            **({"vendor__city_id": selected_city.id} if selected_city else {}),
        )
        .select_related('vendor')
        [:6]
    )



    # =========================================================
    # POPULAR CITIES
    # =========================================================

    popular_cities = (
        City.objects
        .filter(is_active=True)
        .annotate(
            listing_count=Count(
                'listings',
                filter=Q(listings__is_active=True),
                distinct=True
            )
        )
        .filter(listing_count__gt=0)
        .order_by('-listing_count', 'name')[:8]
    )

    trending_services = (
        Service.objects
        .filter(is_active=True)
        .annotate(
            listing_count=Count(
                'listings',
                filter=Q(listings__is_active=True),
                distinct=True
            )
        )
        .filter(listing_count__gt=0)
        .select_related('category')
        .order_by('-listing_count', 'name')[:8]
    )

    # =========================================================
    # BUDGET RANGES
    # =========================================================

    budget_ranges = [
        {
            'label': '₹10K – ₹25K',
            'short_label': '₹10K – ₹25K',
            'description': 'For intimate celebrations',
            'min_price': 10000,
            'max_price': 25000,
        },
        {
            'label': '₹25K – ₹50K',
            'short_label': '₹25K – ₹50K',
            'description': 'Beautiful celebrations',
            'min_price': 25000,
            'max_price': 50000,
        },
        {
            'label': '₹50K – ₹1L',
            'short_label': '₹50K – ₹1L',
            'description': 'Premium wedding services',
            'min_price': 50000,
            'max_price': 100000,
        },
        {
            'label': '₹1L – ₹2.5L',
            'short_label': '₹1L – ₹2.5L',
            'description': 'Grand wedding experiences',
            'min_price': 100000,
            'max_price': 250000,
        },
        {
            'label': '₹2.5L+',
            'short_label': '₹2.5L+',
            'description': 'Luxury celebrations',
            'min_price': 250000,
            'max_price': '',
        },
    ]


    # =========================================================
    # STATS
    # =========================================================

  
  
    stats = {
        'vendor_count': (
            VendorProfile.objects.filter(
                city_id=selected_city.id
            ).count()
            if selected_city
            else VendorProfile.objects.count()
        ),

        'listing_count': (
            Listing.objects.filter(
                is_active=True,
                city_id=selected_city.id
            ).count()
            if selected_city
            else Listing.objects.filter(
                is_active=True
            ).count()
        ),

        'category_count': (
            Category.objects.filter(
                is_active=True,
                listings__is_active=True,
                listings__city_id=selected_city.id
            ).distinct().count()
            if selected_city
            else Category.objects.filter(
                is_active=True
            ).count()
        ),

        'event_type_count': EventType.objects.filter(
            is_active=True
        ).count(),
    }



    cities = (
    City.objects
    .filter(
        is_active=True
    )
    .order_by("name")
    )

    # =========================================================
    # CONTEXT
    # =========================================================

    context = {

        'categories': categories,

        'event_types': event_types,

        'featured_vendors': featured_vendors,

        'featured_packages': featured_packages,

        'popular_cities': popular_cities,

        'trending_services': trending_services,

        'budget_ranges': budget_ranges,

        'stats': stats,

        'states': State.objects.filter(
            is_active=True
        ).order_by('name'),

        'cities': cities,

        'selected_city': selected_city,

    }


    return render(
        request,
        'core/home.html',
        context
    )