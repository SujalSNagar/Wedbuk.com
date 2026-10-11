from categories.models import Category



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
