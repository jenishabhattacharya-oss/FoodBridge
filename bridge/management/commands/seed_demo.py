from datetime import timedelta

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.core.files.storage import default_storage
from django.conf import settings
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from donations.models import Donation
from donors.models import DonorProfile
from ngos.models import NGOProfile
from payments.models import VolunteerPayment, VolunteerPayoutProfile
from volunteers.models import Pickup, VolunteerProfile


DEMO_PREFIX = "[DEMO] "
DEMO_EMAIL_PREFIX = "demo."
DEMO_PASSWORD = "FoodBridgeDemo123!"

# A valid, tiny PNG keeps the demo self-contained without requiring external files.
DEMO_IMAGE = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDAT\x08\xd7c\xf8\xcf\xc0\x00\x00\x03\x01\x01\x00\x18\xdd\x8d\xb1"
    b"\x00\x00\x00\x00IEND\xaeB`\x82"
)


class Command(BaseCommand):
    help = "Create or refresh the isolated FoodBridge demonstration dataset."

    def handle(self, *args, **options):
        with transaction.atomic():
            self._remove_existing_demo_data()
            users = self._create_users()
            donations = self._create_donations(users)
        self._print_summary(users, donations)

    def _remove_existing_demo_data(self):
        donations = Donation.objects.filter(donor__email__startswith=DEMO_EMAIL_PREFIX)
        pickup_ids = list(donations.exclude(pickup_id=None).values_list("pickup_id", flat=True))
        image_names = list(donations.exclude(food_photo_overview="").values_list("food_photo_overview", flat=True))
        image_names += list(donations.exclude(food_photo_closeup="").values_list("food_photo_closeup", flat=True))
        image_names += list(donations.exclude(food_photo_label="").values_list("food_photo_label", flat=True))
        image_names += list(donations.exclude(receipt_photo="").values_list("receipt_photo", flat=True))
        image_names += list(Pickup.objects.filter(pk__in=pickup_ids).exclude(delivery_photo="").values_list("delivery_photo", flat=True))

        VolunteerPayment.objects.filter(pickup_id__in=pickup_ids).delete()
        donations.delete()
        Pickup.objects.filter(pk__in=pickup_ids).delete()
        for name in image_names:
            default_storage.delete(name)

        # The command owns only users whose complete e-mail addresses use this prefix.
        User.objects.filter(email__startswith=DEMO_EMAIL_PREFIX).delete()

    def _user(self, *, email, first_name, last_name, phone, role):
        user = User.objects.create_user(
            email=email,
            password=DEMO_PASSWORD,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            role=role,
        )
        return user

    def _create_users(self):
        donor = self._user(email="demo.donor@foodbridge.local", first_name="Asha", last_name="Donor", phone="9000000001", role=User.Role.DONOR)
        volunteer = self._user(email="demo.volunteer@foodbridge.local", first_name="Vikram", last_name="Volunteer", phone="9000000002", role=User.Role.VOLUNTEER)
        ngo = self._user(email="demo.ngo@foodbridge.local", first_name="Nisha", last_name="NGO", phone="9000000003", role=User.Role.NGO)
        pending_ngo = self._user(email="demo.pending-ngo@foodbridge.local", first_name="Priya", last_name="Pending", phone="9000000004", role=User.Role.NGO)

        DonorProfile.objects.create(
            user=donor,
            address="42 MG Road, Bengaluru, Karnataka",
            city="Bengaluru",
            latitude="12.975600",
            longitude="77.606600",
            place_label="MG Road, Bengaluru",
        )
        VolunteerProfile.objects.create(
            user=volunteer,
            service_area="Bengaluru",
            transport_mode=VolunteerProfile.TransportMode.BICYCLE,
            is_available=True,
            location_sharing_consent=True,
            current_latitude="12.971600",
            current_longitude="77.594600",
            location_updated_at=timezone.now(),
        )
        if settings.PAYMENT_ENCRYPTION_KEY:
            payout_profile = VolunteerPayoutProfile(
                volunteer=volunteer,
                destination=VolunteerPayoutProfile.Destination.UPI,
            )
            payout_profile.set_upi_id("demo.volunteer@upi")
            payout_profile.save()
        NGOProfile.objects.create(
            user=ngo,
            organization_name="Demo Hope Foundation",
            address="18 Indiranagar, Bengaluru, Karnataka",
            latitude="12.978400",
            longitude="77.640800",
            place_label="Demo Hope Foundation, Indiranagar",
            approval_status=NGOProfile.ApprovalStatus.APPROVED,
            approved_at=timezone.now(),
        )
        NGOProfile.objects.create(
            user=pending_ngo,
            organization_name="Demo Pending Food Collective",
            address="Church Street, Bengaluru, Karnataka",
            latitude="12.974000",
            longitude="77.607000",
            place_label="Church Street, Bengaluru",
            approval_status=NGOProfile.ApprovalStatus.PENDING,
        )
        return {"donor": donor, "volunteer": volunteer, "ngo": ngo, "pending_ngo": pending_ngo}

    def _image(self, name):
        return ContentFile(DEMO_IMAGE, name=name)

    def _donation(self, *, title, donor, verification_status, status, hours=1, pickup=True, **extra):
        now = timezone.now()
        donation = Donation.objects.create(
            donor=donor,
            title=f"{DEMO_PREFIX}{title}",
            description=extra.pop("description", "Fresh surplus food prepared for the FoodBridge demonstration."),
            food_type=Donation.FoodType.VEG,
            food_condition=Donation.FoodCondition.COOKED,
            quantity=extra.pop("quantity", 24),
            unit=Donation.Unit.PLATES,
            prepared_at=now - timedelta(minutes=30),
            storage_notes="Kept covered and ready for collection.",
            allergen_notes="Contains gluten.",
            food_photo_overview=self._image("overview.png"),
            food_photo_closeup=self._image("closeup.png"),
            food_photo_label=self._image("label.png"),
            verification_status=verification_status,
            verification_summary=extra.pop("verification_summary", "Demo visual-screening result."),
            verification_confidence=extra.pop("verification_confidence", 92),
            visible_risk_flags=extra.pop("visible_risk_flags", []),
            verification_provider="demo dataset",
            verification_model="local sample",
            verified_at=now,
            pickup_address="42 MG Road, Bengaluru, Karnataka",
            pickup_latitude="12.975600",
            pickup_longitude="77.606600",
            pickup_place_label="MG Road, Bengaluru",
            pickup_window_start=now + timedelta(hours=hours),
            pickup_window_end=now + timedelta(hours=hours + 3),
            status=status,
            **extra,
        )
        if pickup:
            demo_pickup = Pickup.objects.create(
                donor_name=donor.get_full_name(),
                donor_phone=donor.phone,
                pickup_address=donation.pickup_address,
                pickup_city=donor.donor_profile.city,
                pickup_latitude=donation.pickup_latitude,
                pickup_longitude=donation.pickup_longitude,
                pickup_place_label=donation.pickup_place_label,
                food_description=f"{donation.title}: {donation.description}",
                quantity=f"{donation.quantity} {donation.get_unit_display()}",
                pickup_window_start=donation.pickup_window_start,
                pickup_window_end=donation.pickup_window_end,
                instructions="Use the main entrance and ask for the demo coordinator.",
            )
            donation.pickup = demo_pickup
            donation.save(update_fields=("pickup", "updated_at"))
        return donation

    def _create_donations(self, users):
        donor, volunteer, ngo = users["donor"], users["volunteer"], users["ngo"]
        donations = {}
        donations["available"] = self._donation(
            title="Available food listing", donor=donor,
            verification_status=Donation.VerificationStatus.APPROVED,
            status=Donation.Status.AVAILABLE,
        )
        donations["ready_for_volunteer"] = self._donation(
            title="NGO accepted - ready for volunteer", donor=donor,
            verification_status=Donation.VerificationStatus.APPROVED,
            status=Donation.Status.NGO_ACCEPTED,
            receiving_ngo=ngo,
        )
        active = self._donation(
            title="Collected - live location", donor=donor,
            verification_status=Donation.VerificationStatus.APPROVED,
            status=Donation.Status.IN_TRANSIT,
            receiving_ngo=ngo,
        )
        active.pickup.assigned_volunteer = volunteer
        active.pickup.status = Pickup.Status.COLLECTED
        active.pickup.claimed_at = timezone.now() - timedelta(minutes=45)
        active.pickup.collected_at = timezone.now() - timedelta(minutes=15)
        active.pickup.destination_latitude = ngo.ngo_profile.latitude
        active.pickup.destination_longitude = ngo.ngo_profile.longitude
        active.pickup.destination_place_label = ngo.ngo_profile.organization_name
        active.pickup.save()
        donations["in_transit"] = active

        completed = self._donation(
            title="Completed volunteer delivery", donor=donor,
            verification_status=Donation.VerificationStatus.APPROVED,
            status=Donation.Status.DELIVERED,
            receiving_ngo=ngo,
        )
        completed.pickup.assigned_volunteer = volunteer
        completed.pickup.status = Pickup.Status.DELIVERED
        completed.pickup.claimed_at = timezone.now() - timedelta(days=1, hours=2)
        completed.pickup.collected_at = timezone.now() - timedelta(days=1, hours=1)
        completed.pickup.delivered_at = timezone.now() - timedelta(days=1)
        completed.pickup.recipient_name = ngo.ngo_profile.organization_name
        completed.pickup.recipient_address = ngo.ngo_profile.address
        completed.pickup.destination_latitude = ngo.ngo_profile.latitude
        completed.pickup.destination_longitude = ngo.ngo_profile.longitude
        completed.pickup.destination_place_label = ngo.ngo_profile.organization_name
        completed.pickup.handoff_notes = "Delivered to the NGO demonstration coordinator."
        completed.pickup.delivery_photo = self._image("delivery-proof.png")
        completed.pickup.save()
        VolunteerPayment.objects.create(
            pickup=completed.pickup, ngo=ngo, volunteer=volunteer, amount_paise=50000,
            status=VolunteerPayment.Status.PAYOUT_PROCESSED,
            ngo_confirmed_at=timezone.now() - timedelta(days=1),
            paid_at=timezone.now() - timedelta(hours=20),
            payout_released_at=timezone.now() - timedelta(hours=19),
            razorpay_order_id="demo_order_completed",
            razorpay_payment_id="demo_payment_completed",
            razorpay_payout_id="demo_payout_completed",
        )
        donations["completed"] = completed

        donations["review"] = self._donation(
            title="Food safety review required", donor=donor,
            verification_status=Donation.VerificationStatus.HUMAN_REVIEW,
            status=Donation.Status.AVAILABLE, pickup=False,
            verification_summary="Demo images need an NGO reviewer decision.",
            verification_confidence=38, visible_risk_flags=["unclear_image"],
        )
        donations["rejected"] = self._donation(
            title="Food safety screening rejected", donor=donor,
            verification_status=Donation.VerificationStatus.REJECTED,
            status=Donation.Status.AVAILABLE, pickup=False,
            verification_summary="Demo rejection: visible quality concern.",
            verification_confidence=18, visible_risk_flags=["visible_quality_concern"],
        )
        managed = self._donation(
            title="NGO takeover awaiting receipt", donor=donor,
            verification_status=Donation.VerificationStatus.APPROVED,
            status=Donation.Status.NGO_MANAGED,
            claimed_by_ngo=ngo,
        )
        managed.pickup.status = Pickup.Status.CANCELLED
        managed.pickup.save(update_fields=("status", "updated_at"))
        donations["managed"] = managed

        receipt = self._donation(
            title="NGO takeover receipt confirmed", donor=donor,
            verification_status=Donation.VerificationStatus.APPROVED,
            status=Donation.Status.DELIVERED,
            claimed_by_ngo=ngo,
        )
        receipt.pickup.status = Pickup.Status.CANCELLED
        receipt.pickup.save(update_fields=("status", "updated_at"))
        receipt.receipt_photo = self._image("ngo-receipt.png")
        receipt.save(update_fields=("receipt_photo", "updated_at"))
        donations["receipt"] = receipt

        donations["reopened"] = self._donation(
            title="NGO rejection reopened listing", donor=donor,
            verification_status=Donation.VerificationStatus.APPROVED,
            status=Donation.Status.AVAILABLE,
            verification_summary="Returned to the available queue after NGO rejection.",
        )
        return donations

    def _print_summary(self, users, donations):
        self.stdout.write(self.style.SUCCESS("FoodBridge demonstration dataset is ready."))
        self.stdout.write("\nUse this password for every demo account: " + DEMO_PASSWORD)
        for label in ("donor", "volunteer", "ngo", "pending_ngo"):
            self.stdout.write(f"- {label.replace('_', ' ').title()}: {users[label].email}")
        self.stdout.write("\nStart the site with: python manage.py runserver")
        self.stdout.write("Login: http://127.0.0.1:8000" + reverse("login"))
        self.stdout.write("Available food: http://127.0.0.1:8000" + reverse("ngo_donations"))
        self.stdout.write("Food review: http://127.0.0.1:8000" + reverse("food_review_queue"))
        payment = donations["completed"].pickup.volunteer_payment
        self.stdout.write("Payment detail: http://127.0.0.1:8000" + reverse("volunteer_payment_detail", args=[payment.id]))
        self.stdout.write("\nFeatured donation IDs:")
        for label, donation in donations.items():
            self.stdout.write(f"- {label.replace('_', ' ')}: {donation.id} ({donation.title})")
