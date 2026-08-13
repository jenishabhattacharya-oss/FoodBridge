from django.urls import path

from . import views

urlpatterns = [
    path("", views.ngo_list, name="ngo_donations"),
    path("managed/", views.ngo_managed, name="ngo_managed_donations"),
    path("food-review/", views.food_review_queue, name="food_review_queue"),
    path("food-review/<int:donation_id>/<str:decision>/", views.review_food, name="review_food"),
    path("<int:donation_id>/photos/<str:kind>/", views.donation_photo, name="donation_photo"),
    path("new/", views.create, name="donation_create"),
    path("mine/", views.mine, name="my_donations"),
    path("<int:donation_id>/", views.detail, name="donation_detail"),
    path("<int:donation_id>/edit/", views.edit, name="donation_edit"),
    path("<int:donation_id>/cancel/", views.cancel, name="donation_cancel"),
    path("<int:donation_id>/takeover/", views.takeover, name="donation_takeover"),
    path("<int:donation_id>/accept-for-delivery/", views.accept_for_delivery, name="donation_accept_for_delivery"),
    path("<int:donation_id>/reject/", views.reject_ngo_donation, name="donation_reject"),
    path("<int:donation_id>/confirm-receipt/", views.confirm_receipt, name="donation_confirm_receipt"),
]
