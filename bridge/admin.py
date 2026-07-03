from django.contrib import admin
from .models import *

admin.site.register(NGO)
admin.site.register(Donor)
admin.site.register(FoodDonation)
admin.site.register(Volunteer)
admin.site.register(ContactMessage)