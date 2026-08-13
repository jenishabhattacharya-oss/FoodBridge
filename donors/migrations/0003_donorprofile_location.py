from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("donors", "0002_donorprofile_city")]

    operations = [
        migrations.AddField(model_name="donorprofile", name="latitude", field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
        migrations.AddField(model_name="donorprofile", name="longitude", field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
        migrations.AddField(model_name="donorprofile", name="place_label", field=models.CharField(blank=True, max_length=255)),
    ]
