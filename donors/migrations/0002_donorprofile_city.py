# Generated manually for the donation listing feature.
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("donors", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="donorprofile",
            name="city",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
    ]
