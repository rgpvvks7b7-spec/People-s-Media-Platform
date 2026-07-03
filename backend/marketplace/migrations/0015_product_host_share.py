from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("marketplace", "0014_phase7_8_9"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="host_share",
            field=models.DecimalField(decimal_places=2, default=0.00, max_digits=8),
        ),
    ]
