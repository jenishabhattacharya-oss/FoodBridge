from django.contrib.auth import authenticate, login
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.contrib import messages


from .forms import LoginForm
from .registration import FORM_MAP
from .models import User


def register(request):
    if request.method == "POST":
        role = request.POST.get("role")

        FormClass = FORM_MAP.get(role)
        if FormClass is None:
            return HttpResponseBadRequest("Invalid role.")

        form = FormClass(request.POST)

        if form.is_valid():
            form.save()
            return redirect("login")

    else:
        role = request.GET.get("role", User.Role.DONOR)

        FormClass = FORM_MAP.get(role)
        if FormClass is None:
            return HttpResponseBadRequest("Invalid role.")

        form = FormClass()

    return render(
        request,
        "accounts/register.html",
        {
            "form": form,
            "selected_role": role,
            "roles": User.Role,
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

        if user:
            login(request, user)
            return redirect("home")

        messages.error(request, "Invalid email or password.")

    return render(
        request,
        "accounts/login.html",
        {"form": form},
    )
