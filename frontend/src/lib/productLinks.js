const MUSIC_STORE_PRODUCT_TYPES = new Set(["digital_download", "vinyl", "cassette", "beat"]);

export function getProductShopTab(product) {
  return MUSIC_STORE_PRODUCT_TYPES.has(product.product_type) ? "music-store" : "merch";
}

export function buildProductPageUrl(product, {
  origin = typeof window !== "undefined" ? window.location.origin : "",
  pathname = typeof window !== "undefined" ? window.location.pathname : "/",
  artistUsername = "",
  profession = "",
} = {}) {
  const username = artistUsername || product.artist_username || "";
  const prof = product.profession || profession || "music";
  const params = new URLSearchParams({
    artist: username,
    profession: prof,
    tab: getProductShopTab(product),
    product: String(product.id),
  });
  return `${origin}${pathname}?${params.toString()}`;
}

export function readArtistDeepLinkParams(search = "") {
  const params = new URLSearchParams(search || (typeof window !== "undefined" ? window.location.search : ""));
  return {
    tab: params.get("tab") || "",
    productId: params.get("product") || "",
  };
}
