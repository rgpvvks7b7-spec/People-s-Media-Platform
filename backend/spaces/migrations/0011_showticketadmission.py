from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("marketplace", "0015_product_host_share"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("spaces", "0010_host_ticket_payouts"),
    ]

    operations = [
        migrations.CreateModel(
            name="ShowTicketAdmission",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("door_code", models.CharField(db_index=True, max_length=12, unique=True)),
                ("host_verified_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "booking",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="ticket_admissions", to="spaces.spacebooking"),
                ),
                (
                    "fan",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="show_ticket_admissions", to=settings.AUTH_USER_MODEL),
                ),
                (
                    "host_verified_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="verified_door_admissions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "product",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="show_admissions", to="marketplace.product"),
                ),
            ],
            options={
                "ordering": ["-created_at"],
                "unique_together": {("booking", "fan")},
            },
        ),
    ]
