from django.contrib import admin

from .models import Pickup, VolunteerProfile


@admin.register(VolunteerProfile)
class VolunteerProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "service_area", "transport_mode", "is_available")
    list_filter = ("is_available", "transport_mode")
    search_fields = ("user__email", "user__first_name", "user__last_name", "service_area")


@admin.register(Pickup)
class PickupAdmin(admin.ModelAdmin):
    list_display = (
        "donor_name",
        "food_description",
        "pickup_city",
        "pickup_window_start",
        "status",
        "assigned_volunteer",
    )
    list_filter = ("status", "pickup_city", "pickup_window_start")
    search_fields = ("donor_name", "donor_phone", "pickup_address", "food_description")
    readonly_fields = ("claimed_at", "collected_at", "delivered_at", "created_at", "updated_at")
