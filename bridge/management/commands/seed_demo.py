from datetime import timedelta
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
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

DEMO_ASSET_DIRECTORY = Path(__file__).resolve().parent.parent / "demo_assets"
DEMO_FOOD_PROFILES = {
    "thali": {
        "food_type": Donation.FoodType.VEG, "food_condition": Donation.FoodCondition.COOKED,
        "quantity": 24, "unit": Donation.Unit.PLATES, "is_unpackaged": True,
        "description": "Fresh vegetarian thali portions with rice, dal and seasonal sides.",
        "allergen_notes": "Contains dairy and wheat.", "storage_notes": "Kept covered in insulated serving trays.",
        "overview": "thali.jpg", "closeup": "meal-plated.jpg",
    },
    "catered_meals": {
        "food_type": Donation.FoodType.VEG, "food_condition": Donation.FoodCondition.COOKED,
        "quantity": 36, "unit": Donation.Unit.PLATES, "is_unpackaged": True,
        "description": "Vegetarian lunch portions prepared today for a community event.",
        "allergen_notes": "Contains legumes; may contain dairy.", "storage_notes": "Packed in covered food-safe trays.",
        "overview": "meal-containers.jpg", "closeup": "salad-fresh.jpg",
    },
    "bakery": {
        "food_type": Donation.FoodType.BAKERY, "food_condition": Donation.FoodCondition.FRESH,
        "quantity": 6, "unit": Donation.Unit.BOXES, "is_unpackaged": True,
        "description": "Assorted fresh bakery loaves and rolls from this morning.",
        "allergen_notes": "Contains wheat and gluten.", "storage_notes": "Stored in clean bakery boxes.",
        "overview": "bakery-bread.jpg", "closeup": "bread-loaves.jpg",
    },
    "fish_meal": {
        "food_type": Donation.FoodType.NON_VEG, "food_condition": Donation.FoodCondition.COOKED,
        "quantity": 18, "unit": Donation.Unit.PLATES, "is_unpackaged": True,
        "description": "Cooked rice and fish meal portions prepared for lunch service.",
        "allergen_notes": "Contains fish; prepared with coconut.", "storage_notes": "Kept covered and ready for prompt collection.",
        "overview": "kerala-fish-meal.jpg", "closeup": "thali.jpg",
    },
    "salad": {
        "food_type": Donation.FoodType.VEG, "food_condition": Donation.FoodCondition.FRESH,
        "quantity": 12, "unit": Donation.Unit.PACKS, "is_unpackaged": True,
        "description": "Fresh salad packs with leafy greens and seasonal vegetables.",
        "allergen_notes": "Dressing served separately; contains no listed allergens.", "storage_notes": "Chilled until collection.",
        "overview": "salad-fresh.jpg", "closeup": "produce-bowl.jpg",
    },
    "vegetables": {
        "food_type": Donation.FoodType.VEGETABLES, "food_condition": Donation.FoodCondition.FRESH,
        "quantity": 8, "unit": Donation.Unit.KG, "is_unpackaged": True,
        "description": "Fresh seasonal vegetables sorted for a community kitchen.",
        "allergen_notes": "No known allergens.", "storage_notes": "Stored in a cool, clean area.",
        "overview": "vegetables.jpg", "closeup": "produce-bowl.jpg",
    },
    "packaged_meals": {
        "food_type": Donation.FoodType.GROCERIES, "food_condition": Donation.FoodCondition.PACKAGED,
        "quantity": 18, "unit": Donation.Unit.PACKS, "is_unpackaged": False,
        "description": "Sealed vegetarian meal packs and pantry items with package details available for review.",
        "allergen_notes": "Check package labels for allergen details.", "storage_notes": "Sealed packs stored as directed on the packaging.",
        "overview": "meal-containers.jpg", "closeup": "meal-plated.jpg", "label": "food-label-jar.jpg",
    },
    "fruit": {
        "food_type": Donation.FoodType.FRUITS, "food_condition": Donation.FoodCondition.FRESH,
        "quantity": 10, "unit": Donation.Unit.KG, "is_unpackaged": True,
        "description": "A mixed selection of fresh fruit for the afternoon meal service.",
        "allergen_notes": "No known allergens.", "storage_notes": "Washed fruit kept in clean crates.",
        "overview": "fruit-platter.jpg", "closeup": "produce-bowl.jpg",
    },
}


class Command(BaseCommand):
    help = "Create or refresh the isolated FoodBridge demonstration dataset."

    def add_arguments(self, parser):
        parser.add_argument(
            "--allow-production",
            action="store_true",
            help="Explicitly allow demo data creation outside development.",
        )

    def handle(self, *args, **options):
        if not settings.DEBUG and not options["allow_production"]:
            raise CommandError("Demo seeding is disabled outside development.")
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
            approval_status=VolunteerProfile.ApprovalStatus.APPROVED,
            approved_at=timezone.now(),
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

    def _image(self, asset_name, name):
        """Return a bundled photo without relying on network access at seed time."""
        asset_path = DEMO_ASSET_DIRECTORY / asset_name
        return ContentFile(asset_path.read_bytes(), name=name)

    def _donation(self, *, title, donor, verification_status, status, food_profile, hours=1, pickup=True, **extra):
        now = timezone.now()
        food = {**DEMO_FOOD_PROFILES[food_profile]}
        for key in tuple(food):
            if key in extra:
                food[key] = extra.pop(key)
        donation = Donation.objects.create(
            donor=donor,
            title=f"{DEMO_PREFIX}{title}",
            description=food["description"],
            food_type=food["food_type"],
            food_condition=food["food_condition"],
            quantity=food["quantity"],
            unit=food["unit"],
            prepared_at=now - timedelta(minutes=30),
            storage_notes=food["storage_notes"],
            allergen_notes=food["allergen_notes"],
            is_unpackaged=food["is_unpackaged"],
            food_photo_overview=self._image(food["overview"], "food-overview.jpg"),
            food_photo_closeup=self._image(food["closeup"], "food-closeup.jpg"),
            food_photo_label=self._image(food["label"], "food-label.jpg") if food.get("label") else "",
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
            status=Donation.Status.AVAILABLE, food_profile="thali",
        )
        donations["ready_for_volunteer"] = self._donation(
            title="NGO accepted - ready for volunteer", donor=donor,
            verification_status=Donation.VerificationStatus.APPROVED,
            status=Donation.Status.NGO_ACCEPTED,
            food_profile="catered_meals",
            receiving_ngo=ngo,
        )
        active = self._donation(
            title="Collected - live location", donor=donor,
            verification_status=Donation.VerificationStatus.APPROVED,
            status=Donation.Status.IN_TRANSIT,
            food_profile="bakery",
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
            food_profile="fish_meal",
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
        completed.pickup.delivery_photo = self._image("food-distribution.jpg", "delivery-proof.jpg")
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
            status=Donation.Status.AVAILABLE, food_profile="salad", pickup=False,
            verification_summary="Demo images need an NGO reviewer decision.",
            verification_confidence=38, visible_risk_flags=["unclear_image"],
        )
        donations["rejected"] = self._donation(
            title="Food safety screening rejected", donor=donor,
            verification_status=Donation.VerificationStatus.REJECTED,
            status=Donation.Status.AVAILABLE, food_profile="vegetables", pickup=False,
            verification_summary="Demo rejection: visible quality concern.",
            verification_confidence=18, visible_risk_flags=["visible_quality_concern"],
        )
        managed = self._donation(
            title="NGO takeover awaiting receipt", donor=donor,
            verification_status=Donation.VerificationStatus.APPROVED,
            status=Donation.Status.NGO_MANAGED,
            food_profile="fruit",
            claimed_by_ngo=ngo,
        )
        managed.pickup.status = Pickup.Status.CANCELLED
        managed.pickup.save(update_fields=("status", "updated_at"))
        donations["managed"] = managed

        receipt = self._donation(
            title="NGO takeover receipt confirmed", donor=donor,
            verification_status=Donation.VerificationStatus.APPROVED,
            status=Donation.Status.DELIVERED,
            food_profile="packaged_meals",
            claimed_by_ngo=ngo,
        )
        receipt.pickup.status = Pickup.Status.CANCELLED
        receipt.pickup.save(update_fields=("status", "updated_at"))
        receipt.receipt_photo = self._image("food-distribution.jpg", "ngo-receipt.jpg")
        receipt.save(update_fields=("receipt_photo", "updated_at"))
        donations["receipt"] = receipt

        donations["reopened"] = self._donation(
            title="NGO rejection reopened listing", donor=donor,
            verification_status=Donation.VerificationStatus.APPROVED,
            status=Donation.Status.AVAILABLE,
            food_profile="fruit",
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
