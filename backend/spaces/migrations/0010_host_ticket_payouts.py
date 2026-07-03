from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("spaces", "0009_booking_dismiss_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="hostprofile",
            name="pending_ticket_earnings",
            field=models.DecimalField(decimal_places=2, default=0.00, max_digits=10),
        ),
        migrations.AddField(
            model_name="hostprofile",
            name="stripe_connect_account_id",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="hostprofile",
            name="stripe_connect_onboarded_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
