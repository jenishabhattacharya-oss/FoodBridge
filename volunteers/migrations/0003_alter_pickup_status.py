# Generated manually for donation cancellation support.
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("volunteers", "0002_volunteerprofile_is_available_and_more")]

    operations = [
        migrations.AlterField(
            model_name="pickup",
            name="status",
            field=models.CharField(
                choices=[
                    ("OPEN", "Open"),
                    ("CLAIMED", "Claimed"),
                    ("COLLECTED", "Collected"),
                    ("DELIVERED", "Delivered"),
                    ("CANCELLED", "Cancelled"),
                ],
                db_index=True,
                default="OPEN",
                max_length=20,
            ),
        ),
    ]
