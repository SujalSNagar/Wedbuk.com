from django.urls import path

from . import views


app_name = 'vendors'


urlpatterns = [

    path(
        'onboarding/',
        views.onboarding,
        name='onboarding'
    ),

    path(
        'dashboard/',
        views.dashboard,
        name='dashboard'
    ),

    path(
        'profile/edit/',
        views.edit_profile,
        name='edit_profile'
    ),

    path(
        'cities/',
        views.cities_by_state,
        name='cities_by_state'
    ),

]