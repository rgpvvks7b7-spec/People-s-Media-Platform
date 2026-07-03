from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("spaces", "0002_phase7_8_9"),
    ]

    operations = [
        migrations.CreateModel(
            name="SpaceListingPhoto",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("image", models.ImageField(upload_to="spaces/listings/")),
                ("photo_type", models.CharField(
                    choices=[
                        ("stage", "Stage / band setup"),
                        ("audience", "Audience area"),
                        ("room_overview", "Room overview"),
                        ("load_in", "Load-in / access"),
                        ("other", "Other"),
                    ],
                    default="room_overview",
                    max_length=40,
                )),
                ("caption", models.CharField(blank=True, max_length=180)),
                ("sort_order", models.PositiveSmallIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("listing", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="gallery_photos", to="spaces.spacelisting")),
            ],
            options={
                "ordering": ["sort_order", "id"],
            },
        ),
    ]
