from django.urls import path

from . import views

urlpatterns = [
    path("ngo/connect/", views.connect_razorpay, name="connect_razorpay"),
    path("ngo/oauth/callback/", views.oauth_callback, name="razorpay_oauth_callback"),
    path("volunteer/payout-profile/", views.payout_profile, name="volunteer_payout_profile"),
    path("pickups/<int:pickup_id>/confirm-delivery/", views.confirm_volunteer_delivery, name="confirm_volunteer_delivery"),
    path("volunteer-payments/<int:payment_id>/", views.volunteer_payment_detail, name="volunteer_payment_detail"),
    path("volunteer-payments/<int:payment_id>/order/", views.create_payment_order, name="create_payment_order"),
    path("volunteer-payments/<int:payment_id>/verify/", views.verify_payment_callback, name="verify_payment_callback"),
    path("volunteer-payments/<int:payment_id>/release/", views.release_volunteer_payout, name="release_volunteer_payout"),
    path("webhooks/razorpay/", views.razorpay_webhook, name="razorpay_webhook"),
]
