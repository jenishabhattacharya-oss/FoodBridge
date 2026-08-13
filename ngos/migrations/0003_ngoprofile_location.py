from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("ngos", "0002_ngoprofile_address")]

    operations = [
        migrations.AddField(model_name="ngoprofile", name="latitude", field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
        migrations.AddField(model_name="ngoprofile", name="longitude", field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
        migrations.AddField(model_name="ngoprofile", name="place_label", field=models.CharField(blank=True, max_length=255)),
    ]
