export function upsertMetaTag(attribute, key, content) {
  if (!content) return;
  let tag = document.head.querySelector(`meta[${attribute}="${key}"]`);
  if (!tag) {
    tag = document.createElement("meta");
    tag.setAttribute(attribute, key);
    document.head.appendChild(tag);
  }
  tag.setAttribute("content", content);
}

export function updateArtistPageMeta(artistMeta) {
  if (!artistMeta) {
    document.title = "INDIEFUND";
    upsertMetaTag("name", "description", "Direct fan support for independent artists.");
    upsertMetaTag("property", "og:title", "INDIEFUND");
    upsertMetaTag("property", "og:description", "Direct fan support for independent artists.");
    upsertMetaTag("property", "og:url", window.location.origin);
    upsertMetaTag("property", "og:type", "website");
    return;
  }

  document.title = artistMeta.title || `${artistMeta.stage_name} on IndieFund`;
  upsertMetaTag("name", "description", artistMeta.description);
  upsertMetaTag("property", "og:title", artistMeta.title || artistMeta.stage_name);
  upsertMetaTag("property", "og:description", artistMeta.description);
  upsertMetaTag("property", "og:url", artistMeta.page_url || window.location.href);
  upsertMetaTag("property", "og:type", "profile");
  if (artistMeta.hero_image) {
    upsertMetaTag("property", "og:image", artistMeta.hero_image);
  }
}

export async function fetchArtistMeta(apiBase, username, profession = "") {
  const query = profession ? `?profession=${encodeURIComponent(profession)}` : "";
  const response = await fetch(`${apiBase}/artists/public/${encodeURIComponent(username)}/${query}`, {
    credentials: "include",
  });
  if (!response.ok) return null;
  return response.json();
}

export function updateLegalPageMeta(page) {
  if (!page) {
    updateArtistPageMeta(null);
    return;
  }
  const title = `${page.title} | IndieFund`;
  document.title = title;
  upsertMetaTag("name", "description", page.description);
  upsertMetaTag("property", "og:title", title);
  upsertMetaTag("property", "og:description", page.description);
  upsertMetaTag("property", "og:url", `${window.location.origin}${window.location.pathname}?page=${page.id}`);
  upsertMetaTag("property", "og:type", "website");
}
