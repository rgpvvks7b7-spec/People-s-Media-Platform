from django.http import HttpResponse
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response

from config.platform_mode import is_prelaunch
from artists.models import ArtistProfile


def resolve_public_profession(profile, requested_profession=""):
    profession_keys = profile.profession_list()
    if requested_profession in profession_keys:
        return requested_profession
    return profession_keys[0] if profession_keys else ArtistProfile.DEFAULT_PROFESSION


def build_public_artist_page_url(request, username, profession=""):
    base = request.build_absolute_uri("/").rstrip("/")
    params = f"artist={username}"
    if profession:
        params = f"{params}&profession={profession}"
    return f"{base}/?{params}"


def serialize_public_artist_meta(profile, profession, request):
    profession_profile = profile.profession_profiles.filter(profession=profession).first()
    cover = ""
    if profession_profile and profession_profile.cover_image:
        cover = profession_profile.cover_image.url
    elif profile.hero_image:
        cover = profile.hero_image.url
    if cover and request:
        cover = request.build_absolute_uri(cover)

    display_title = (
        (profession_profile.display_title if profession_profile else "")
        or profile.stage_name
    )
    description_source = (
        (profession_profile.bio if profession_profile else "")
        or profile.artist_story
        or (profession_profile.style if profession_profile else "")
        or profile.genre
        or ""
    ).strip()
    if len(description_source) > 180:
        description_source = f"{description_source[:177]}..."

    profession_label = ArtistProfile.profession_label(profession)
    page_url = build_public_artist_page_url(request, profile.owner.username, profession)
    title = f"{display_title} — {profession_label} on IndieFund"

    return {
        "owner_id": profile.owner_id,
        "username": profile.owner.username,
        "stage_name": profile.stage_name,
        "display_title": display_title,
        "genre": profile.genre,
        "city": profile.city,
        "profession": profession,
        "profession_keys": profile.profession_list(),
        "description": description_source or f"Support {display_title} on IndieFund.",
        "hero_image": cover,
        "page_url": page_url,
        "title": title,
        "profession_label": profession_label,
        "on_hiatus": profile.on_hiatus,
    }


@api_view(["GET"])
def public_artist_meta(request, username):
    try:
        profile = (
            ArtistProfile.objects
            .select_related("owner")
            .prefetch_related("profession_profiles")
            .get(owner__username=username, owner__user_type="artist")
        )
    except ArtistProfile.DoesNotExist:
        return Response({"error": "Artist not found"}, status=404)

    requested_profession = (request.query_params.get("profession") or "").strip()
    profession = resolve_public_profession(profile, requested_profession)
    return Response(serialize_public_artist_meta(profile, profession, request))


def robots_txt(request):
    sitemap_url = request.build_absolute_uri("/sitemap.xml")
    lines = ["User-agent: *"]
    if is_prelaunch():
        lines.extend([
            "Allow: /?artist=",
            "Allow: /api/artists/public/",
            "Disallow: /?page=listen",
            "Disallow: /?page=stores",
            "Disallow: /?page=my-scene",
            "Disallow: /?page=discover",
            "Disallow: /?page=feed",
        ])
    else:
        lines.append("Allow: /")
    lines.extend([f"Sitemap: {sitemap_url}", ""])
    return HttpResponse("\n".join(lines), content_type="text/plain")


def sitemap_xml(request):
    profiles = ArtistProfile.objects.select_related("owner").order_by("-created_at")[:500]
    base = request.build_absolute_uri("/").rstrip("/")
    now = timezone.now().date().isoformat()
    urls = []
    if not is_prelaunch():
        urls.append(f"  <url><loc>{base}/</loc><lastmod>{now}</lastmod></url>")
    for profile in profiles:
        professions = profile.profession_list() or [ArtistProfile.DEFAULT_PROFESSION]
        for profession in professions:
            urls.append(
                f"  <url><loc>{base}/?artist={profile.owner.username}&amp;profession={profession}</loc><lastmod>{now}</lastmod></url>"
            )
    xml = "\n".join([
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
        *urls,
        "</urlset>",
    ])
    return HttpResponse(xml, content_type="application/xml")
