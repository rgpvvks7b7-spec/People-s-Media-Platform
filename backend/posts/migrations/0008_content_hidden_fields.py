from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("posts", "0007_alter_pointofview_profession_alter_post_profession"),
    ]

    operations = [
        migrations.AddField(
            model_name="post",
            name="is_hidden",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="comment",
            name="is_hidden",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="instant",
            name="is_hidden",
            field=models.BooleanField(default=False),
        ),
    ]
