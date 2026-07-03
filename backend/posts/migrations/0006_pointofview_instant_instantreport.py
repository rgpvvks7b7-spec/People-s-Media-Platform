from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("posts", "0005_post_profession"),
    ]

    operations = [
        migrations.CreateModel(
            name="Instant",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("body", models.TextField(max_length=280)),
                ("media", models.FileField(blank=True, null=True, upload_to="instants/")),
                ("visibility", models.CharField(choices=[("followers", "Followers"), ("supporters", "Supporters"), ("public", "Public")], default="followers", max_length=20)),
                ("expires_at", models.DateTimeField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("artist", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="instants", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="PointOfView",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("profession", models.CharField(blank=True, choices=[("music", "Music"), ("visual_art", "Painting / Drawing"), ("digital_art", "Digital Art"), ("craft", "Crafts"), ("writing", "Writing"), ("performance", "Performance"), ("other", "Other")], max_length=40)),
                ("body", models.TextField(max_length=500)),
                ("is_pinned", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("artist", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="points_of_view", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="InstantReport",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("reason", models.CharField(blank=True, max_length=240)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("instant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="reports", to="posts.instant")),
                ("reporter", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="instant_reports", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-created_at"],
                "unique_together": {("instant", "reporter")},
            },
        ),
        migrations.AddIndex(
            model_name="instant",
            index=models.Index(fields=["artist", "expires_at"], name="posts_insta_artist__f10870_idx"),
        ),
        migrations.AddIndex(
            model_name="instant",
            index=models.Index(fields=["visibility", "expires_at"], name="posts_insta_visibil_462924_idx"),
        ),
    ]
