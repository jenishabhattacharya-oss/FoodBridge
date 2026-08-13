from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("volunteers", "0004_pickup_workspace_indexes")]

    operations = [
        migrations.AddField(model_name="volunteerprofile", name="location_sharing_consent", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="volunteerprofile", name="current_latitude", field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
        migrations.AddField(model_name="volunteerprofile", name="current_longitude", field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
        migrations.AddField(model_name="volunteerprofile", name="location_updated_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="pickup", name="pickup_latitude", field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
        migrations.AddField(model_name="pickup", name="pickup_longitude", field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
        migrations.AddField(model_name="pickup", name="pickup_place_label", field=models.CharField(blank=True, max_length=255)),
        migrations.AddField(model_name="pickup", name="destination_latitude", field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
        migrations.AddField(model_name="pickup", name="destination_longitude", field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
        migrations.AddField(model_name="pickup", name="destination_place_label", field=models.CharField(blank=True, max_length=255)),
    ]
