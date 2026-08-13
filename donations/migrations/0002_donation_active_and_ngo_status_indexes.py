from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("donations", "0001_initial"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="donation",
            index=models.Index(
                fields=["status", "pickup_window_end"],
                name="donation_active_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="donation",
            index=models.Index(
                fields=["claimed_by_ngo", "status"],
                name="donation_ngo_status_idx",
            ),
        ),
    ]
