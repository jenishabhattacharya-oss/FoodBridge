from django.urls import reverse


def sidebar(active_label):
    items = (
        ("Dashboard", "bi-speedometer2", "ngo_dashboard"),
        ("Available food", "bi-basket2-fill", "ngo_donations"),
        ("Managed donations", "bi-clipboard2-check", "ngo_managed_donations"),
        ("Food safety review", "bi-shield-check", "food_review_queue"),
    )
    return [
        {"label": label, "icon": icon, "url": reverse(url_name), "active": label == active_label}
        for label, icon, url_name in items
    ]
