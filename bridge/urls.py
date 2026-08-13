from django.urls import path
from . import views

urlpatterns = [
    path("health/", views.health, name="health"),
    path("location/geocode/", views.geocode, name="location_geocode"),
    path("", views.index, name="home"),
    path("donate", views.donate, name="donate"),
    path("contact", views.contact, name="contact"),
]
