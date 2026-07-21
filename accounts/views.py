from django.contrib.auth import authenticate, login
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.contrib import messages
from django.contrib.auth import logout

from .forms import LoginForm
from .registration import ROLE_REGISTRY
from .models import User
from .utils import get_dashboard_url


def register(request):
    role = (
        request.POST.get("role")
        if request.method == "POST"
        else request.GET.get("role", User.Role.DONOR)
    )

    role_info = ROLE_REGISTRY.get(role)

    if role_info is None:
        return HttpResponseBadRequest("Invalid role.")

    form_class = role_info["form"]

    if request.method == "POST":
        form = form_class(request.POST)

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "Your account has been created successfully. Please sign in.",
            )

            return redirect("login")

    else:
        form = form_class()

    return render(
        request,
        "accounts/register.html",
        {
            "form": form,
            "selected_role": role,
            "roles": ROLE_REGISTRY,
            "base_fields": {
                "email",
                "first_name",
                "last_name",
                "phone",
                "password",
                "confirm_password",
            },
        },
    )


def login_view(request):
    form = LoginForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        user = authenticate(
            request,
            email=form.cleaned_data["email"],
            password=form.cleaned_data["password"],
        )

        if user is not None:
            login(request, user)

            messages.success(
                request,
                f"Welcome back, {user.first_name}!",
            )

            return redirect(get_dashboard_url(user))

        form.add_error(
            None,
            "Invalid email or password.",
        )

    return render(
        request,
        "accounts/login.html",
        {"form": form},
    )


def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect("home")
