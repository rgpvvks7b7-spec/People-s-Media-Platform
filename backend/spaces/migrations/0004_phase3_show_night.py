import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("spaces", "0003_spacelistingphoto"),
    ]

    operations = [
        migrations.AddField(
            model_name="spacebooking",
            name="check_in_token",
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name="spacebooking",
            name="ticket_inventory",
            field=models.PositiveIntegerField(default=0, help_text="0 uses venue capacity; set explicitly to cap ticket sales."),
        ),
        migrations.CreateModel(
            name="ShowCheckIn",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("checked_in_at", models.DateTimeField(auto_now_add=True)),
                ("booking", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="check_ins", to="spaces.spacebooking")),
                ("fan", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="show_check_ins", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-checked_in_at"],
                "unique_together": {("booking", "fan")},
            },
        ),
    ]
