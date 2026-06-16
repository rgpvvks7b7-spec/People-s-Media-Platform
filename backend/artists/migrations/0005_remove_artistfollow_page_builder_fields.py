# Generated manually to correct 0004, which accidentally added page-builder
# fields to ArtistFollow as well as ArtistProfile.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("artists", "0004_artistfollow_show_about_artistfollow_show_lives_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="artistfollow",
            name="show_about",
        ),
        migrations.RemoveField(
            model_name="artistfollow",
            name="show_lives",
        ),
        migrations.RemoveField(
            model_name="artistfollow",
            name="show_music",
        ),
        migrations.RemoveField(
            model_name="artistfollow",
            name="show_posts",
        ),
        migrations.RemoveField(
            model_name="artistfollow",
            name="show_store",
        ),
    ]
