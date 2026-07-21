# Create your views here.
from django.contrib.auth.decorators import login_required

from accounts.decorators import role_required
from accounts.models import User

from django.shortcuts import render


@login_required
@role_required(User.Role.DONOR)
def dashboard(request):
    return render(request, "donors/dashboard.html")
