from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("mediahub", "0002_musicupload_profession"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ArtworkUpload",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("profession", models.CharField(choices=[("music", "Music"), ("visual_art", "Painting / Drawing"), ("digital_art", "Digital Art"), ("craft", "Crafts"), ("writing", "Writing"), ("performance", "Performance"), ("other", "Other")], default="visual_art", max_length=40)),
                ("title", models.CharField(max_length=160)),
                ("image", models.ImageField(upload_to="artworks/")),
                ("description", models.TextField(blank=True)),
                ("medium", models.CharField(blank=True, max_length=120)),
                ("dimensions", models.CharField(blank=True, max_length=80)),
                ("year", models.PositiveIntegerField(blank=True, null=True)),
                ("availability", models.CharField(choices=[("available", "Available"), ("sold", "Sold"), ("print_only", "Print only"), ("not_for_sale", "Not for sale")], default="available", max_length=40)),
                ("is_supporter_only", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("artist", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="artwork_uploads", to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
