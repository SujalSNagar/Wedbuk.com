from django.contrib import admin

from .models import (
    Listing,
    ListingAttributeValue,
    ListingImage,
    ListingVideo,
    ListingAvailability,
    ListingBlockedDate,
)


# =========================================================
# LISTING IMAGE INLINE
# =========================================================

class ListingImageInline(admin.TabularInline):

    model = ListingImage

    extra = 1

    fields = (
        'image',
        'display_order',
    )


# =========================================================
# LISTING VIDEO INLINE
# =========================================================

class ListingVideoInline(admin.TabularInline):

    model = ListingVideo

    extra = 1

    fields = (
        'video',
        'display_order',
    )


# =========================================================
# AVAILABILITY INLINE
# =========================================================

class ListingAvailabilityInline(admin.TabularInline):

    model = ListingAvailability

    extra = 1

    fields = (
        'available_from',
        'available_until',
        'is_active',
    )


# =========================================================
# BLOCKED DATE INLINE
# =========================================================

class ListingBlockedDateInline(admin.TabularInline):

    model = ListingBlockedDate

    extra = 1

    fields = (
        'date',
        'reason',
    )


# =========================================================
# ATTRIBUTE VALUE INLINE
# =========================================================

class ListingAttributeValueInline(admin.TabularInline):

    model = ListingAttributeValue

    extra = 0

    fields = (
        'attribute',
        'value',
    )


# =========================================================
# LISTING ADMIN
# =========================================================

@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):

    list_display = (
        'title',
        'vendor',
        'category',
        'base_price',
        'is_active',
        'created_at',
    )

    list_filter = (
        'category',
        'is_active',
        'event_types',
    )

    search_fields = (
        'title',
        'vendor__business_name',
        'description',
    )

    filter_horizontal = (
        'event_types',
        'services',
    )

    readonly_fields = (
        'created_at',
        'updated_at',
    )

    inlines = [
        ListingImageInline,
        ListingVideoInline,
        ListingAvailabilityInline,
        ListingBlockedDateInline,
        ListingAttributeValueInline,
    ]


# =========================================================
# LISTING IMAGE ADMIN
# =========================================================

@admin.register(ListingImage)
class ListingImageAdmin(admin.ModelAdmin):

    list_display = (
        'listing',
        'display_order',
        'created_at',
    )

    list_filter = (
        'listing',
    )

    search_fields = (
        'listing__title',
        'listing__vendor__business_name',
    )

    ordering = (
        'listing',
        'display_order',
    )


# =========================================================
# LISTING VIDEO ADMIN
# =========================================================

@admin.register(ListingVideo)
class ListingVideoAdmin(admin.ModelAdmin):

    list_display = (
        'listing',
        'display_order',
        'created_at',
    )

    list_filter = (
        'listing',
    )

    search_fields = (
        'listing__title',
        'listing__vendor__business_name',
    )

    ordering = (
        'listing',
        'display_order',
    )


# =========================================================
# LISTING AVAILABILITY ADMIN
# =========================================================

@admin.register(ListingAvailability)
class ListingAvailabilityAdmin(admin.ModelAdmin):

    list_display = (
        'listing',
        'available_from',
        'available_until',
        'is_active',
    )

    list_filter = (
        'is_active',
    )

    search_fields = (
        'listing__title',
        'listing__vendor__business_name',
    )


# =========================================================
# LISTING BLOCKED DATE ADMIN
# =========================================================

@admin.register(ListingBlockedDate)
class ListingBlockedDateAdmin(admin.ModelAdmin):

    list_display = (
        'listing',
        'date',
        'reason',
        'created_at',
    )

    list_filter = (
        'date',
    )

    search_fields = (
        'listing__title',
        'listing__vendor__business_name',
        'reason',
    )