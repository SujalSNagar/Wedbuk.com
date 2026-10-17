from categories.models import Category


from locations.models import City


def selected_city_context(request):
    city_id = request.session.get("selected_city_id")

    selected_city = None

    if city_id:
        selected_city = City.objects.filter(
            id=city_id,
            is_active=True,
            state__is_active=True,
        ).first()

        if selected_city is None:
            request.session.pop("selected_city_id", None)

    return {
        "selected_city": selected_city,
    }



def header_categories(request):

    categories = (
        Category.objects
        .filter(
            is_active=True
        )
        .order_by(
            'name'
        )
    )

    return {
        'header_categories': categories
    }


def footer_data(request):
    return {
        'footer_categories': Category.objects.filter(
            is_active=True
        ).order_by('name')[:6]
    }



def selected_city(request):
    return {
        "selected_city": getattr(request, "selected_city", None)
    }
