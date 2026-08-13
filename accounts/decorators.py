from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect


def approved_ngo_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        profile = getattr(request.user, "ngo_profile", None)
        if profile is None or not profile.is_approved:
            messages.info(request, "Your NGO account is awaiting FoodBridge staff approval.")
            return redirect("ngo_dashboard")
        return view_func(request, *args, **kwargs)

    return wrapper


def role_required(*allowed_roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect("login")

            if request.user.role not in allowed_roles:
                messages.error(
                    request,
                    "You are not authorized to access this page.",
                )
                return redirect("home")

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator
