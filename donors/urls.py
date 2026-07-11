from django.urls import path
from . import views

app_name = "donors"

urlpatterns = [
    path("register/", views.donor_register, name="register"),
]
