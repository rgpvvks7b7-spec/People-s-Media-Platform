from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("spaces", "0005_alter_spacebookingreview_reviewee_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="spacebooking",
            name="material_url",
            field=models.URLField(blank=True, max_length=500),
        ),
        migrations.AddField(
            model_name="spacebooking",
            name="material_credit",
            field=models.CharField(blank=True, max_length=200),
        ),
    ]
