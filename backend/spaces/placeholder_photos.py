import hashlib
import io

from django.core.files.base import ContentFile
from PIL import Image, ImageDraw, ImageFont

from .models import SpaceListingPhoto


def _listing_seed(listing):
    raw = f"{listing.id}:{listing.name}:{listing.city}".encode()
    return int(hashlib.sha256(raw).hexdigest()[:8], 16)


def _palette(seed):
    palettes = [
        ((24, 24, 32), (168, 85, 247), (255, 196, 86)),
        ((18, 28, 38), (14, 165, 233), (244, 114, 182)),
        ((28, 22, 18), (245, 158, 11), (251, 191, 36)),
        ((20, 30, 24), (16, 185, 129), (110, 231, 183)),
        ((30, 18, 24), (244, 63, 94), (253, 164, 175)),
        ((22, 22, 30), (99, 102, 241), (196, 181, 253)),
    ]
    return palettes[seed % len(palettes)]


def _load_fonts():
    try:
        return (
            ImageFont.truetype("Arial.ttf", 28),
            ImageFont.truetype("Arial.ttf", 18),
        )
    except OSError:
        default = ImageFont.load_default()
        return default, default


def _gradient_background(size, top_color, bottom_color):
    width, height = size
    image = Image.new("RGB", size, top_color)
    draw = ImageDraw.Draw(image)
    for y in range(height):
        ratio = y / max(height - 1, 1)
        color = tuple(int(top_color[i] * (1 - ratio) + bottom_color[i] * ratio) for i in range(3))
        draw.line([(0, y), (width, y)], fill=color)
    return image, draw


def _draw_stage_scene(draw, size, accent, warm):
    width, height = size
    floor_y = int(height * 0.78)
    draw.polygon(
        [
            (int(width * 0.12), floor_y),
            (int(width * 0.88), floor_y),
            (int(width * 0.78), int(height * 0.92)),
            (int(width * 0.22), int(height * 0.92)),
        ],
        fill=(36, 36, 48),
    )
    draw.rectangle((int(width * 0.18), int(height * 0.42), int(width * 0.82), floor_y), fill=(28, 28, 36))
    for x_ratio in (0.28, 0.5, 0.72):
        x = int(width * x_ratio)
        draw.polygon([(x, 0), (x - 40, floor_y), (x + 40, floor_y)], fill=tuple(max(0, c - 40) for c in accent))
        draw.ellipse((x - 18, int(height * 0.08), x + 18, int(height * 0.16)), fill=warm)
    draw.rectangle((int(width * 0.47), int(height * 0.34), int(width * 0.49), int(height * 0.58)), fill=(210, 210, 220))
    draw.ellipse((int(width * 0.44), int(height * 0.31), int(width * 0.52), int(height * 0.36)), fill=(180, 180, 190))
    for x in range(int(width * 0.2), int(width * 0.8), 36):
        draw.rectangle((x, floor_y - 28, x + 18, floor_y - 8), fill=(55, 55, 68))


def _draw_bar_scene(draw, size, accent, warm):
    width, height = size
    counter_y = int(height * 0.62)
    draw.rectangle((0, counter_y, width, int(height * 0.72)), fill=(62, 42, 28))
    draw.rectangle((0, counter_y - 10, width, counter_y), fill=(92, 62, 38))
    for index in range(10):
        x = int(width * 0.08) + index * int(width * 0.085)
        bottle_h = 40 + (index % 3) * 18
        draw.rectangle((x, counter_y - bottle_h, x + 22, counter_y - 8), fill=accent)
        draw.rectangle((x + 4, counter_y - bottle_h - 8, x + 18, counter_y - bottle_h), fill=warm)
    for index in range(4):
        x = int(width * 0.12) + index * int(width * 0.2)
        draw.ellipse((x, counter_y + 18, x + 70, counter_y + 58), fill=(48, 48, 58))
        draw.rectangle((x + 8, counter_y + 10, x + 62, counter_y + 24), fill=(70, 70, 82))
    draw.line([(0, int(height * 0.84)), (width, int(height * 0.84))], fill=(40, 40, 48), width=3)


def _draw_room_scene(draw, size, accent, warm):
    width, height = size
    draw.rectangle((0, int(height * 0.55), width, height), fill=(34, 34, 42))
    draw.rectangle((int(width * 0.08), int(height * 0.18), int(width * 0.92), int(height * 0.55)), fill=(46, 46, 58))
    draw.rectangle((int(width * 0.28), int(height * 0.28), int(width * 0.72), int(height * 0.52)), fill=(58, 58, 72))
    for row in range(3):
        for col in range(5):
            x = int(width * 0.14) + col * int(width * 0.14)
            y = int(height * 0.58) + row * 34
            draw.ellipse((x, y, x + 44, y + 28), fill=accent if (row + col) % 2 else warm)
    draw.line([(int(width * 0.1), int(height * 0.18)), (int(width * 0.9), int(height * 0.18))], fill=(220, 220, 230), width=4)


def build_space_photo_jpeg(listing, photo_type, caption):
    seed = _listing_seed(listing) + sum(ord(char) for char in photo_type)
    bg_dark, accent, warm = _palette(seed)
    bg_light = tuple(min(255, c + 35) for c in bg_dark)
    image, draw = _gradient_background((960, 640), bg_light, bg_dark)

    if photo_type == SpaceListingPhoto.STAGE:
        _draw_stage_scene(draw, image.size, accent, warm)
    elif photo_type == SpaceListingPhoto.AUDIENCE:
        _draw_bar_scene(draw, image.size, accent, warm)
    else:
        _draw_room_scene(draw, image.size, accent, warm)

    title_font, caption_font = _load_fonts()
    label = dict(SpaceListingPhoto.PHOTO_TYPES).get(photo_type, "Venue")
    draw.rounded_rectangle((24, 24, 420, 96), radius=16, fill=(0, 0, 0))
    draw.text((40, 42), listing.name[:34], fill=(255, 255, 255), font=title_font)
    draw.text((40, 72), f"{label} · {listing.city or 'Demo venue'}", fill=(220, 220, 230), font=caption_font)
    draw.text((40, 590), caption[:72], fill=(200, 200, 210), font=caption_font)

    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=88)
    return buffer.getvalue()


def default_gallery_specs(listing):
    venue = listing.name.split("—")[0].strip()
    return [
        (
            SpaceListingPhoto.STAGE,
            0,
            f"{venue} stage — PA ready for live sets.",
        ),
        (
            SpaceListingPhoto.AUDIENCE,
            1,
            f"{venue} bar and seating area.",
        ),
        (
            SpaceListingPhoto.ROOM_OVERVIEW,
            2,
            f"Room overview at {listing.city or 'the venue'}.",
        ),
    ]


def ensure_listing_gallery(listing, *, force=False):
    """Attach generic stage/bar photos when a listing has no gallery yet."""
    if listing.gallery_photos.exists() and not force:
        return listing.gallery_photos.count()

    if force:
        listing.gallery_photos.all().delete()

    created = 0
    for photo_type, sort_order, caption in default_gallery_specs(listing):
        jpeg = build_space_photo_jpeg(listing, photo_type, caption)
        slug = listing.name.lower().replace(" ", "-").replace("—", "-")[:40]
        filename = f"{slug}-{photo_type}-{listing.id or 'new'}.jpg"
        SpaceListingPhoto.objects.create(
            listing=listing,
            photo_type=photo_type,
            caption=caption,
            sort_order=sort_order,
            image=ContentFile(jpeg, name=filename),
        )
        created += 1
    return created


def ensure_all_listing_galleries(*, force=False):
    from .models import SpaceListing

    total_photos = 0
    listings_updated = 0
    for listing in SpaceListing.objects.all().iterator():
        before = listing.gallery_photos.count()
        if before and not force:
            continue
        added = ensure_listing_gallery(listing, force=force)
        if added:
            listings_updated += 1
            total_photos += added
    return listings_updated, total_photos
