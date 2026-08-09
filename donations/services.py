from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from volunteers.models import Pickup, VolunteerProfile

from .models import Donation


def _pickup_values(donation):
    return {
        "donor_name": donation.donor.get_full_name(),
        "donor_phone": donation.donor.phone,
        "pickup_address": donation.pickup_address,
        "pickup_city": donation.donor.donor_profile.city,
        "food_description": f"{donation.title}: {donation.description}",
        "quantity": f"{donation.quantity} {donation.get_unit_display()}",
        "pickup_window_start": donation.pickup_window_start,
        "pickup_window_end": donation.pickup_window_end,
        "instructions": "\n".join(part for part in (
            f"Prepared: {donation.prepared_at:%Y-%m-%d %H:%M}",
            f"Condition: {donation.get_food_condition_display()}",
            f"Storage: {donation.storage_notes}" if donation.storage_notes else "",
            f"Allergens: {donation.allergen_notes}" if donation.allergen_notes else "",
        ) if part),
    }


@transaction.atomic
def create_donation(*, donor, cleaned_data):
    donation = Donation(donor=donor, **cleaned_data)
    donation.full_clean()
    donation.save()
    pickup = Pickup(**_pickup_values(donation))
    pickup.full_clean()
    pickup.save()
    donation.pickup = pickup
    donation.save(update_fields=("pickup", "updated_at"))
    return donation


@transaction.atomic
def update_donation(*, donation_id, donor, cleaned_data):
    donation = Donation.objects.select_for_update().select_related("pickup", "donor__donor_profile").get(pk=donation_id, donor=donor)
    if not donation.can_be_changed or donation.pickup.status != Pickup.Status.OPEN:
        raise ValidationError("This donation can no longer be changed.")
    for field, value in cleaned_data.items():
        setattr(donation, field, value)
    donation.full_clean()
    pickup = donation.pickup
    for field, value in _pickup_values(donation).items():
        setattr(pickup, field, value)
    pickup.full_clean()
    pickup.save()
    donation.save()
    return donation


@transaction.atomic
def cancel_donation(*, donation_id, donor):
    donation = Donation.objects.select_for_update().select_related("pickup").get(pk=donation_id, donor=donor)
    if not donation.can_be_changed or donation.pickup.status != Pickup.Status.OPEN:
        raise ValidationError("This donation can no longer be cancelled.")
    donation.pickup.status = Pickup.Status.CANCELLED
    donation.pickup.full_clean()
    donation.pickup.save(update_fields=("status", "updated_at"))
    donation.status = Donation.Status.CANCELLED
    donation.save(update_fields=("status", "updated_at"))
    return donation


def eligible_volunteers(city):
    active = (Pickup.Status.CLAIMED, Pickup.Status.COLLECTED)
    return VolunteerProfile.objects.filter(is_available=True, service_area__iexact=city).exclude(user__assigned_pickups__status__in=active)


@transaction.atomic
def takeover_donation(*, donation_id, ngo):
    donation = Donation.objects.select_for_update().select_related("pickup", "donor__donor_profile").get(pk=donation_id)
    if not donation.can_be_changed or donation.pickup.status != Pickup.Status.OPEN:
        raise ValidationError("This donation is no longer available for NGO takeover.")
    if eligible_volunteers(donation.donor.donor_profile.city).exists():
        raise ValidationError("An eligible volunteer is available for this pickup.")
    donation.pickup.status = Pickup.Status.CANCELLED
    donation.pickup.full_clean()
    donation.pickup.save(update_fields=("status", "updated_at"))
    donation.claimed_by_ngo = ngo
    donation.status = Donation.Status.NGO_MANAGED
    donation.save(update_fields=("claimed_by_ngo", "status", "updated_at"))
    return donation


@transaction.atomic
def confirm_ngo_receipt(*, donation_id, ngo, receipt_photo):
    donation = Donation.objects.select_for_update().get(pk=donation_id, claimed_by_ngo=ngo)
    if donation.status != Donation.Status.NGO_MANAGED:
        raise ValidationError("This donation is not awaiting NGO receipt confirmation.")
    donation.receipt_photo = receipt_photo
    donation.status = Donation.Status.DELIVERED
    donation.full_clean()
    donation.save()
    return donation


@transaction.atomic
def release_ngo_donation(*, donation_id, ngo):
    """Return an NGO-managed, unexpired donation to the open pickup queue."""
    donation = Donation.objects.select_for_update().select_related("pickup").get(pk=donation_id)

    if donation.claimed_by_ngo_id != ngo.id:
        raise ValidationError("Only the NGO that accepted this donation can reject it.")
    if donation.status != Donation.Status.NGO_MANAGED:
        raise ValidationError("Only donations awaiting NGO receipt can be rejected.")
    if donation.pickup_window_end <= timezone.now():
        raise ValidationError("This donation's pickup window has expired and cannot be reopened.")
    if donation.pickup_id is None:
        raise ValidationError("This donation has no pickup record to reopen.")

    pickup = donation.pickup
    pickup.status = Pickup.Status.OPEN
    pickup.assigned_volunteer = None
    pickup.claimed_at = None
    pickup.collected_at = None
    pickup.delivered_at = None
    pickup.recipient_name = ""
    pickup.recipient_address = ""
    pickup.handoff_notes = ""
    pickup.delivery_photo = ""
    pickup.full_clean()
    pickup.save()

    donation.claimed_by_ngo = None
    donation.status = Donation.Status.AVAILABLE
    donation.full_clean()
    donation.save(update_fields=("claimed_by_ngo", "status", "updated_at"))
    return donation
