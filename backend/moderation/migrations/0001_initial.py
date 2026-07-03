from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ContentReport",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("target_type", models.CharField(choices=[("post", "Post"), ("comment", "Comment"), ("instant", "Instant"), ("user", "User"), ("artist", "Artist profile")], max_length=20)),
                ("target_id", models.PositiveIntegerField()),
                ("reason", models.CharField(choices=[("spam", "Spam"), ("harassment", "Harassment"), ("inappropriate", "Inappropriate content"), ("other", "Other")], default="other", max_length=40)),
                ("details", models.TextField(blank=True)),
                ("status", models.CharField(choices=[("open", "Open"), ("dismissed", "Dismissed"), ("removed", "Removed")], default="open", max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("resolved_at", models.DateTimeField(blank=True, null=True)),
                ("reporter", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="content_reports_filed", to=settings.AUTH_USER_MODEL)),
                ("resolved_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="content_reports_resolved", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="UserBlock",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("blocked", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="blocks_received", to=settings.AUTH_USER_MODEL)),
                ("blocker", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="blocks_initiated", to=settings.AUTH_USER_MODEL)),
            ],
            options={"unique_together": {("blocker", "blocked")}},
        ),
        migrations.CreateModel(
            name="UserMute",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("muted", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="mutes_received", to=settings.AUTH_USER_MODEL)),
                ("muter", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="mutes_initiated", to=settings.AUTH_USER_MODEL)),
            ],
            options={"unique_together": {("muter", "muted")}},
        ),
        migrations.AddIndex(
            model_name="contentreport",
            index=models.Index(fields=["target_type", "target_id"], name="moderation__target__a1b2c3_idx"),
        ),
        migrations.AddIndex(
            model_name="contentreport",
            index=models.Index(fields=["status", "created_at"], name="moderation__status__d4e5f6_idx"),
        ),
    ]
