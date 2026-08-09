from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("volunteers", "0002_volunteerprofile_is_available_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="Donation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=120)), ("description", models.TextField()),
                ("food_type", models.CharField(choices=[("VEG", "Vegetarian"), ("NON_VEG", "Non-vegetarian"), ("BAKERY", "Bakery"), ("GROCERIES", "Groceries"), ("FRUITS", "Fruits"), ("VEGETABLES", "Vegetables")], max_length=20)),
                ("food_condition", models.CharField(choices=[("COOKED", "Cooked"), ("FRESH", "Fresh"), ("PACKAGED", "Packaged")], max_length=20)),
                ("quantity", models.PositiveIntegerField()), ("unit", models.CharField(choices=[("KG", "kg"), ("PACKS", "packs"), ("PLATES", "plates"), ("BOXES", "boxes")], max_length=20)),
                ("prepared_at", models.DateTimeField()), ("storage_notes", models.TextField(blank=True)), ("allergen_notes", models.TextField(blank=True)),
                ("pickup_address", models.TextField()), ("pickup_window_start", models.DateTimeField()), ("pickup_window_end", models.DateTimeField()),
                ("status", models.CharField(choices=[("AVAILABLE", "Available"), ("VOLUNTEER_CLAIMED", "Volunteer claimed"), ("IN_TRANSIT", "In transit"), ("DELIVERED", "Delivered"), ("NGO_MANAGED", "NGO managed"), ("EXPIRED", "Expired"), ("CANCELLED", "Cancelled")], db_index=True, default="AVAILABLE", max_length=24)),
                ("receipt_photo", models.ImageField(blank=True, upload_to="ngo_receipts/%Y/%m/")), ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
                ("claimed_by_ngo", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="managed_donations", to=settings.AUTH_USER_MODEL)),
                ("donor", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="donations", to=settings.AUTH_USER_MODEL)),
                ("pickup", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="donation", to="volunteers.pickup")),
            ],
            options={"ordering": ("-created_at", "-id")},
        ),
    ]
