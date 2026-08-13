from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from .location import request_ip_location, search_places

def index(request):
    return render(request,'index.html')
def donate(request):
    return redirect("donation_create")
def contact(request):
    return render(request, 'contact.html')


@login_required(login_url="login")
@require_GET
def geocode(request):
    query = request.GET.get("q", "").strip()
    if len(query) < 3:
        return JsonResponse({"results": []})
    try:
        latitude = float(request.GET["lat"])
        longitude = float(request.GET["lon"])
        if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
            raise ValueError
    except (KeyError, ValueError):
        latitude, longitude = request_ip_location(request) or (None, None)
    city = getattr(getattr(request.user, "donor_profile", None), "city", "")
    try:
        return JsonResponse({"results": search_places(query, latitude=latitude, longitude=longitude, city=city)})
    except Exception:
        return JsonResponse({"detail": "Location search is temporarily unavailable."}, status=503)
