from django.shortcuts import render, redirect
from .forms import DonorRegistrationForm


# Create your views here.
def donor_register(request):
    if request.method == "POST":
        form = DonorRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("login")
    else:
        form = DonorRegistrationForm()

    return render(request, "donors/register.html", {"form": form})
