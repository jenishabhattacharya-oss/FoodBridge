from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone

from accounts.models import User

from .models import Pickup, VolunteerProfile


class PickupWorkflowError(Exception):
    """Base exception for user-facing pickup workflow failures."""


class PickupUnavailable(PickupWorkflowError):
    pass


class ActivePickupLimitReached(PickupWorkflowError):
    pass


class PickupAccessDenied(PickupWorkflowError):
    pass


class InvalidPickupTransition(PickupWorkflowError):
    pass


def _donation_for(pickup):
    try:
        return pickup.donation
    except ObjectDoesNotExist:
        return None


def _sync_donation(pickup, status):
    donation = _donation_for(pickup)
    if donation:
        donation.status = status
        donation.save(update_fields=("status", "updated_at"))


def create_pickup(**pickup_data):
    """Create an open pickup for staff or future donor-module integrations."""
    pickup = Pickup(**pickup_data)
    pickup.status = Pickup.Status.OPEN
    pickup.assigned_volunteer = None
    pickup.full_clean()
    pickup.save()
    return pickup


@transaction.atomic
def claim_pickup(*, pickup_id, volunteer):
    User.objects.select_for_update().get(pk=volunteer.pk)
    pickup = Pickup.objects.select_for_update().get(pk=pickup_id)
    if pickup.status != Pickup.Status.OPEN:
        raise PickupUnavailable("This pickup is no longer available.")
    donation = _donation_for(pickup)
    if donation:
        if donation.is_expired:
            raise PickupUnavailable("This donation has expired.")
        if donation.status != donation.Status.NGO_ACCEPTED or not donation.receiving_ngo_id:
            raise PickupUnavailable("An NGO must accept this donation before a volunteer can claim it.")
    profile, _ = VolunteerProfile.objects.get_or_create(user=volunteer)
    if not profile.is_available:
        raise PickupUnavailable("Set your availability to available before claiming a pickup.")
    if Pickup.objects.filter(
        assigned_volunteer=volunteer,
        status__in=(Pickup.Status.CLAIMED, Pickup.Status.COLLECTED),
    ).exists():
        raise ActivePickupLimitReached("You already have an active pickup.")

    pickup.mark_claimed(volunteer)
    pickup.full_clean()
    pickup.save()
    if donation:
        _sync_donation(pickup, donation.Status.VOLUNTEER_CLAIMED)
    return pickup


@transaction.atomic
def mark_collected(*, pickup_id, volunteer):
    pickup = Pickup.objects.select_for_update().get(pk=pickup_id)
    if pickup.assigned_volunteer_id != volunteer.id:
        raise PickupAccessDenied("Only the assigned volunteer can update this pickup.")
    if pickup.status != Pickup.Status.CLAIMED:
        raise InvalidPickupTransition("Only claimed pickups can be marked collected.")
    pickup.mark_collected()
    pickup.full_clean()
    pickup.save()
    donation = _donation_for(pickup)
    if donation:
        _sync_donation(pickup, donation.Status.IN_TRANSIT)
    return pickup


@transaction.atomic
def mark_delivered(*, pickup_id, volunteer, recipient_name, recipient_address, handoff_notes, delivery_photo):
    pickup = Pickup.objects.select_for_update().get(pk=pickup_id)
    if pickup.assigned_volunteer_id != volunteer.id:
        raise PickupAccessDenied("Only the assigned volunteer can update this pickup.")
    if pickup.status != Pickup.Status.COLLECTED:
        raise InvalidPickupTransition("Only collected pickups can be marked delivered.")

    pickup.recipient_name = recipient_name
    pickup.recipient_address = recipient_address
    pickup.handoff_notes = handoff_notes
    pickup.delivery_photo = delivery_photo
    pickup.status = Pickup.Status.DELIVERED
    pickup.delivered_at = timezone.now()
    pickup.full_clean()
    pickup.save()
    donation = _donation_for(pickup)
    if donation:
        _sync_donation(pickup, donation.Status.AWAITING_NGO_CONFIRMATION)
    return pickup
