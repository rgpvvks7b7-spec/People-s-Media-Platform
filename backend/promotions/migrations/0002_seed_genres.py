from django.db import migrations


SEED_GENRES = [
    ("hip-hop", "Hip-Hop", "hiphop, rap, boom-bap, boom bap, trap"),
    ("rnb", "R&B", "r&b, rhythm and blues, soul, neo-soul"),
    ("pop", "Pop", "pop, indie-pop, synthpop"),
    ("rock", "Rock", "rock, indie-rock, alt-rock, punk, garage"),
    ("electronic", "Electronic", "edm, electronic, house, techno, dnb, drum and bass"),
    ("country", "Country", "country, americana, alt-country, folk"),
    ("metal", "Metal", "metal, hardcore, metalcore"),
    ("jazz", "Jazz", "jazz, swing, bebop"),
    ("classical", "Classical", "classical, orchestral, instrumental"),
    ("reggae", "Reggae", "reggae, dub, ska, dancehall"),
    ("latin", "Latin", "latin, reggaeton, salsa, cumbia"),
    ("folk", "Folk", "folk, acoustic, singer-songwriter"),
    ("world", "World", "world, afrobeat, afrobeats"),
    ("ambient", "Ambient", "ambient, lo-fi, lofi, chillout"),
]


def seed_genres(apps, schema_editor):
    Genre = apps.get_model("promotions", "Genre")
    for slug, name, aliases in SEED_GENRES:
        Genre.objects.get_or_create(slug=slug, defaults={"name": name, "aliases": aliases})


def unseed_genres(apps, schema_editor):
    Genre = apps.get_model("promotions", "Genre")
    Genre.objects.filter(slug__in=[slug for slug, _, _ in SEED_GENRES]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("promotions", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_genres, unseed_genres),
    ]
