from django.urls import path

from . import views

urlpatterns = [
    path("dashboard/", views.dashboard, name="donor_dashboard"),
    path("profile/", views.profile, name="donor_profile"),
]
