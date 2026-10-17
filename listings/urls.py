from django.urls import path

from . import views


app_name = 'listings'


urlpatterns = [

    # =====================================================
    # SEARCH
    # =====================================================

    path(
        'search/',
        views.search,
        name='search'
    ),


    # =====================================================
    # CITIES
    # =====================================================

    path(
        'cities/',
        views.cities_by_state,
        name='cities_by_state'
    ),

    path(
        'category-attributes/',
        views.category_attributes,
        name='category_attributes'
    ),


    # =====================================================
    # ADD LISTING
    # =====================================================

    path(
        'add/',
        views.add_listing,
        name='add_listing'
    ),


    # =====================================================
    # MY LISTINGS
    # =====================================================

    path(
        'my-listings/',
        views.my_listings,
        name='my_listings'
    ),


    # =====================================================
    # LISTING IMAGE
    # =====================================================

    path(
        '<int:listing_id>/images/add/',
        views.add_listing_image,
        name='add_listing_image'
    ),

    path(
        'images/<int:image_id>/delete/',
        views.delete_listing_image,
        name='delete_listing_image'
    ),


    # =====================================================
    # AVAILABILITY MANAGEMENT
    # =====================================================

    path(
        '<int:listing_id>/availability/add/',
        views.add_availability,
        name='add_availability'
    ),

    path(
        'availability/<int:availability_id>/delete/',
        views.delete_availability,
        name='delete_availability'
    ),


    # =====================================================
    # BLOCKED DATES
    # =====================================================

    path(
        '<int:listing_id>/blocked-date/add/',
        views.add_blocked_date,
        name='add_blocked_date'
    ),

    path(
        'blocked-date/<int:blocked_date_id>/delete/',
        views.delete_blocked_date,
        name='delete_blocked_date'
    ),


    # =====================================================
    # CUSTOMER AVAILABILITY API
    # =====================================================

    path(
        '<int:listing_id>/availability/',
        views.listing_availability,
        name='listing_availability'
    ),


    # =====================================================
    # EDIT LISTING
    # =====================================================

    path(
        '<int:listing_id>/edit/',
        views.edit_listing,
        name='edit_listing'
    ),


    # =====================================================
    # DELETE LISTING
    # =====================================================

    path(
        '<int:listing_id>/delete/',
        views.delete_listing,
        name='delete_listing'
    ),


    # =====================================================
    # LISTING DETAIL
    # =====================================================

    path(
        '<int:listing_id>/',
        views.listing_detail,
        name='listing_detail'
    ),


    # =====================================================
    # CATEGORY DETAIL
    # =====================================================

    path(
        'category/<slug:slug>/',
        views.category_detail,
        name='category_detail'
    ),

    path(
        '<int:listing_id>/cover/delete/',
        views.delete_cover_image,
        name='delete_cover_image'
    ),

    # =====================================================
    # DELETE LISTING VIDEO
    # =====================================================

    path(
        'listing/video/<int:video_id>/delete/',
        views.delete_listing_video,
        name='delete_listing_video'
    ),

    path(
    'budget-results/',
    views.budget_results,
    name='budget_results'
    ),

    path(
    'filter/',
    views.filter_results,
    name='filter_results'
),


path(
    "select-city/",
    views.select_city,
    name="select_city",
),

]