from django.contrib import admin

from .models import Donation


@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = ("title", "donor", "status", "pickup_window_end", "created_at")
    list_filter = ("status", "food_type", "food_condition")
    search_fields = ("title", "donor__email", "pickup_address")
