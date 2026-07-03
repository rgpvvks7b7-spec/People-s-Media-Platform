from django.db import migrations


def grandfather_existing_releases(apps, schema_editor):
    ReleaseApproval = apps.get_model("originlock", "ReleaseApproval")
    ContentType = apps.get_model("contenttypes", "ContentType")
    MusicUpload = apps.get_model("mediahub", "MusicUpload")
    Product = apps.get_model("marketplace", "Product")

    def approve_existing(model, file_attr):
        content_type = ContentType.objects.get_for_model(model)
        rows = []
        existing_ids = set(
            ReleaseApproval.objects.filter(content_type=content_type).values_list("object_id", flat=True)
        )
        for obj in model.objects.all().iterator():
            if obj.id in existing_ids:
                continue
            if not getattr(obj, file_attr, None):
                continue
            rows.append(
                ReleaseApproval(
                    artist_id=obj.artist_id,
                    user_id=obj.artist_id,
                    content_type=content_type,
                    object_id=obj.id,
                    approval_status="approved",
                    approval_method="admin",
                    approved_at=obj.created_at,
                    file_name=getattr(obj, file_attr).name[:255],
                )
            )
        ReleaseApproval.objects.bulk_create(rows, batch_size=200)

    approve_existing(MusicUpload, "audio_file")
    approve_existing(Product, "product_file")


def remove_grandfathered_releases(apps, schema_editor):
    ReleaseApproval = apps.get_model("originlock", "ReleaseApproval")
    ReleaseApproval.objects.filter(approval_method="admin").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("originlock", "0001_initial"),
        ("mediahub", "0008_alter_artworkupload_profession_and_more"),
        ("marketplace", "0015_product_host_share"),
    ]

    operations = [
        migrations.RunPython(grandfather_existing_releases, remove_grandfathered_releases),
    ]
