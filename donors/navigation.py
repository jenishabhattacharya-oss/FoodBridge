from django.urls import reverse


def sidebar(active_label):
    """Navigation shared by every screen in the donor workspace."""
    items = (
        ("Dashboard", "bi-speedometer2", "donor_dashboard"),
        ("Donate food", "bi-basket2-fill", "donation_create"),
        ("My donations", "bi-card-list", "my_donations"),
        ("My profile", "bi-person-gear", "donor_profile"),
    )
    return [
        {
            "label": label,
            "icon": icon,
            "url": reverse(url_name),
            "active": label == active_label,
        }
        for label, icon, url_name in items
    ]
