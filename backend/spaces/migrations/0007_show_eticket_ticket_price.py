from decimal import Decimal

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("spaces", "0006_spacebooking_artist_material"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="spacebooking",
            name="ticket_price",
            field=models.DecimalField(decimal_places=2, default=Decimal("15.00"), max_digits=8),
        ),
        migrations.CreateModel(
            name="ShowETicket",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("ticket_code", models.CharField(max_length=64, unique=True)),
                ("issued_at", models.DateTimeField(auto_now_add=True)),
                ("redeemed_at", models.DateTimeField(blank=True, null=True)),
                ("booking", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="etickets", to="spaces.spacebooking")),
                ("fan", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="show_etickets", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-issued_at"],
                "unique_together": {("booking", "fan")},
            },
        ),
    ]
