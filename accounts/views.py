from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import (
    RegisterForm,
    VendorRegisterForm,
    LoginForm,
)

from .models import User
from vendors.models import VendorProfile


def register_view(request):

    if request.user.is_authenticated:
        return redirect('core:home')

    if request.method == 'POST':

        form = RegisterForm(request.POST)

        if form.is_valid():

            new_user = User.objects.create_user(
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password'],
                full_name=form.cleaned_data['full_name'],
                phone_number=form.cleaned_data['phone_number'],
                role=User.Role.CUSTOMER,
            )

            login(request, new_user)

            messages.success(
                request,
                'Your account has been created successfully.'
            )

            return redirect('core:home')

    else:

        form = RegisterForm()

    return render(
        request,
        'accounts/register.html',
        {
            'form': form
        }
    )


def vendor_register_view(request):

    if request.user.is_authenticated:
        return redirect('core:home')

    if request.method == 'POST':

        form = VendorRegisterForm(
            request.POST
        )

        if form.is_valid():

            new_user = User.objects.create_user(
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password'],
                full_name=form.cleaned_data['full_name'],
                phone_number=form.cleaned_data['phone_number'],
                role=User.Role.VENDOR,
            )

            VendorProfile.objects.create(
                user=new_user,
                business_name=form.cleaned_data[
                    'business_name'
                ],
            )

            login(request, new_user)

            messages.success(
                request,
                'Your vendor account has been created successfully.'
            )

            return redirect(
                'vendors:onboarding'
            )

    else:

        form = VendorRegisterForm()

    return render(
        request,
        'accounts/vendor_register.html',
        {
            'form': form
        }
    )


def login_view(request):

    if request.user.is_authenticated:

        return redirect(
            'core:home'
        )


    if request.method == 'POST':

        form = LoginForm(
            request.POST,
            request=request
        )


        if form.is_valid():

            user = form.cleaned_data['user']

            login(
                request,
                user
            )


            messages.success(
                request,
                'You have logged in successfully.'
            )


            # =================================================
            # VENDOR LOGIN
            # =================================================

            if user.role == User.Role.VENDOR:

                vendor_profile = VendorProfile.objects.filter(
                    user=user
                ).first()


                # ---------------------------------------------
                # Vendor profile does not exist
                # ---------------------------------------------

                if not vendor_profile:

                    return redirect(
                        'vendors:onboarding'
                    )


                # ---------------------------------------------
                # Vendor onboarding is incomplete
                #
                # Required:
                # 1. Business Name
                # 2. State
                # 3. City
                # 4. At least one Category
                # ---------------------------------------------

                if (
                    not vendor_profile.state_id
                    or not vendor_profile.city_id
                    or not vendor_profile.categories.exists()
                ):

                    return redirect(
                        'vendors:onboarding'
                    )


                # ---------------------------------------------
                # Vendor onboarding completed
                # ---------------------------------------------

                return redirect(
                    'vendors:dashboard'
                )


            # =================================================
            # CUSTOMER LOGIN
            # =================================================

            return redirect(
                'core:home'
            )


    else:

        form = LoginForm(
            request=request
        )


    return render(
        request,
        'accounts/login.html',
        {
            'form': form
        }
    )


def logout_view(request):

    logout(request)

    messages.success(
        request,
        'You have been logged out successfully.'
    )

    return redirect(
        'core:home'
    )