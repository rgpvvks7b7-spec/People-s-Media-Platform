from decimal import Decimal
from django.db import migrations, models


def backfill_product_fees(apps, schema_editor):
    Product = apps.get_model("marketplace", "Product")
    for product in Product.objects.all():
        price = Decimal(str(product.price))
        platform_fee = (price * Decimal("0.15")).quantize(Decimal("0.01"))
        product.platform_fee = platform_fee
        product.artist_share = price - platform_fee
        product.save(update_fields=["artist_share", "platform_fee"])


class Migration(migrations.Migration):

    dependencies = [
        ("marketplace", "0011_commissionrequest"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="artist_share",
            field=models.DecimalField(decimal_places=2, default=0.0, max_digits=8),
        ),
        migrations.AddField(
            model_name="product",
            name="platform_fee",
            field=models.DecimalField(decimal_places=2, default=0.0, max_digits=8),
        ),
        migrations.AddField(
            model_name="commissionrequest",
            name="quoted_artist_share",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True),
        ),
        migrations.AddField(
            model_name="commissionrequest",
            name="quoted_platform_fee",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True),
        ),
        migrations.RunPython(backfill_product_fees, migrations.RunPython.noop),
    ]
