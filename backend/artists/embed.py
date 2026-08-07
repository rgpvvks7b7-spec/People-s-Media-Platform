from django.http import HttpResponse
from django.utils.html import escape
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny

from artists.models import ArtistProfile

from .public import resolve_public_profession, serialize_public_artist_meta


EMBED_CSS = """
:root {
  color-scheme: dark;
  --bg: #14121c;
  --ink: #f4f0ff;
  --muted: rgba(244, 240, 255, 0.68);
  --accent: #c4b5fd;
  --line: rgba(255, 255, 255, 0.12);
}
* { box-sizing: border-box; }
html, body {
  margin: 0;
  padding: 0;
  width: 100%;
  height: 100%;
  background: transparent;
  font-family: "Avenir Next", "Segoe UI", sans-serif;
}
a.card {
  display: flex;
  gap: 14px;
  align-items: center;
  width: 100%;
  height: 100%;
  min-height: 148px;
  padding: 16px;
  text-decoration: none;
  color: var(--ink);
  background:
    radial-gradient(120% 140% at 0% 0%, rgba(196, 181, 253, 0.22), transparent 55%),
    linear-gradient(160deg, #1c1828, var(--bg));
  border: 1px solid var(--line);
  border-radius: 18px;
}
.cover {
  width: 72px;
  height: 72px;
  border-radius: 14px;
  object-fit: cover;
  background: rgba(255, 255, 255, 0.08);
  flex: 0 0 auto;
}
.cover--empty {
  display: grid;
  place-items: center;
  font-weight: 700;
  color: var(--accent);
}
.copy { min-width: 0; }
.eyebrow {
  margin: 0 0 4px;
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--accent);
}
h1 {
  margin: 0;
  font-size: 20px;
  line-height: 1.15;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
p {
  margin: 6px 0 0;
  font-size: 13px;
  color: var(--muted);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.cta {
  margin-top: 10px;
  display: inline-flex;
  align-items: center;
  padding: 7px 12px;
  border-radius: 999px;
  background: var(--accent);
  color: #1a1328;
  font-size: 12px;
  font-weight: 700;
}
"""


def render_artist_embed_html(meta):
    stage = escape(meta["display_title"] or meta["stage_name"])
    genre = escape(meta.get("genre") or "")
    city = escape(meta.get("city") or "")
    description = escape(meta.get("description") or f"Support {meta['display_title']} on IndieFund.")
    page_url = escape(meta["page_url"])
    title = escape(meta["title"])
    cover = meta.get("hero_image") or ""
    meta_bits = " · ".join(bit for bit in [genre, city] if bit)

    if cover:
        cover_html = f'<img class="cover" src="{escape(cover)}" alt="" />'
    else:
        initial = escape((meta["display_title"] or meta["stage_name"] or "?")[:1].upper())
        cover_html = f'<div class="cover cover--empty" aria-hidden="true">{initial}</div>'

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title}</title>
  <style>{EMBED_CSS}</style>
</head>
<body>
  <a class="card" href="{page_url}" target="_blank" rel="noopener noreferrer">
    {cover_html}
    <div class="copy">
      <p class="eyebrow">IndieFund</p>
      <h1>{stage}</h1>
      <p>{description if description else meta_bits}</p>
      <span class="cta">Support on IndieFund</span>
    </div>
  </a>
</body>
</html>
"""


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def public_artist_embed(request, username):
    try:
        profile = (
            ArtistProfile.objects
            .select_related("owner")
            .prefetch_related("profession_profiles")
            .get(owner__username=username, owner__user_type="artist")
        )
    except ArtistProfile.DoesNotExist:
        return HttpResponse("Artist not found", status=404, content_type="text/plain")

    profession = resolve_public_profession(profile, (request.query_params.get("profession") or "").strip())
    meta = serialize_public_artist_meta(profile, profession, request)
    response = HttpResponse(render_artist_embed_html(meta), content_type="text/html; charset=utf-8")
    # Allow third-party sites to iframe this widget.
    if "X-Frame-Options" in response:
        del response["X-Frame-Options"]
    response["Content-Security-Policy"] = "frame-ancestors *"
    response["Cache-Control"] = "public, max-age=300"
    return response
