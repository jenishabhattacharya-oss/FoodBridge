from django.urls import path

from . import views

urlpatterns = [
    path("dashboard/", views.dashboard, name="ngo_dashboard"),
    path("profile/", views.profile, name="ngo_profile"),
]
