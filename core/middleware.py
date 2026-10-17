
from locations.models import City


class SelectedCityMiddleware:
    """
    Makes the session-selected city available on every request.
    The city is temporary and stored only in the Django session.
    """

    SESSION_KEY = "selected_city_id"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        city_id = request.session.get(self.SESSION_KEY)
        selected_city = None

        if city_id:
            selected_city = (
                City.objects
                .filter(id=city_id, is_active=True)
                .first()
            )

            # Invalid/deleted/inactive city: clear stale selection.
            if selected_city is None:
                request.session.pop(self.SESSION_KEY, None)

        request.selected_city = selected_city

        return self.get_response(request)
