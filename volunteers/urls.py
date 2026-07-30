from django.urls import path

from . import views

urlpatterns = [
    path("dashboard/", views.dashboard, name="volunteer_dashboard"),
    path(
        "pickups/",
        views.available_pickups,
        name="available_pickups",
    ),
    path(
        "pickups/<int:pickup_id>/",
        views.pickup_details,
        name="pickup_details",
    ),
    path(
        "pickups/<int:pickup_id>/accept/",
        views.accept_pickup,
        name="accept_pickup",
    ),
    path(
        "assigned/",
        views.assigned_pickups,
        name="assigned_pickups",
    ),
    path(
        "history/",
        views.pickup_history,
        name="pickup_history",
    ),
]
