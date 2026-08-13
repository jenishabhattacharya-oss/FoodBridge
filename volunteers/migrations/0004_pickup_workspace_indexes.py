from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("volunteers", "0003_alter_pickup_status"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="pickup",
            index=models.Index(
                fields=["status", "pickup_city", "pickup_window_start"],
                name="pickup_open_city_time_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="pickup",
            index=models.Index(
                fields=["assigned_volunteer", "status"],
                name="pickup_volunteer_status_idx",
            ),
        ),
    ]
