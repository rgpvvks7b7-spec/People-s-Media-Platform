/**
 * Theme IDs are stable for saved user/artist preferences.
 * Tributes evoke era, palette, and mood only — never logos, likeness, or artwork.
 */
export const DEFAULT_THEME = "theme-indie-dark";
export const DEFAULT_HOST_THEME = "theme-host-warm-hearth";

export const THEME_OPTIONS = [
  { id: "theme-indie-dark", label: "IndieFund Dark", group: "platform", blurb: "Black canvas, purple accent, subtle grid glow." },
  { id: "theme-retro-vhs", label: "Retro VHS", group: "platform", blurb: "CRT scanlines, magenta/cyan bleed, 90s tape warmth." },
  { id: "theme-clean-label", label: "Clean Label", group: "platform", blurb: "Bright minimal label-site with crisp card shadows." },
  { id: "theme-boombap", label: "Boom Bap", group: "platform", blurb: "Vinyl-warm amber, crate-dig brown, soft groove texture." },
  { id: "theme-neon-club", label: "Neon Club", group: "platform", blurb: "Late-night dancefloor — pink pulse and cyan edge glow." },
  { id: "theme-accessible-dark", label: "Accessible Dark", group: "accessible", blurb: "High-contrast dark mode — blue and orange accents, no red/green reliance." },
  { id: "theme-accessible-light", label: "Accessible Light", group: "accessible", blurb: "High-contrast light mode — colour-blind-safe blue and orange on white." },
  { id: "theme-tribute-purple-rain", label: "Tribute: Prince", group: "tribute", blurb: "Slow-falling pixel raindrops and a blocky purple puddle at the footer (palette & mood only)." },
  { id: "theme-tribute-alien-pop", label: "Tribute: Oliver Tree", group: "tribute", blurb: "Neon skatepark scanlines — electric yellow, blue, and pink flicker on black (vibe only, no artwork)." },
  { id: "theme-tribute-gold-frame", label: "Tribute: Marvin Gaye", group: "tribute", blurb: "Velvet soul with shimmering vinyl rings and honey-gold frames (palette & mood only)." },
  { id: "theme-tribute-starman", label: "Tribute: David Bowie", group: "tribute", blurb: "Twinkling pixel stars, galaxy dust, and lightning-orange cosmic navy (palette & mood only)." },
  { id: "theme-tribute-neon-angel", label: "Tribute: Avicii", group: "tribute", blurb: "Rising equalizer bars and euphoric halo blues for a night-drive glow (palette & mood only)." },
  { id: "theme-tribute-midnight-piano", label: "Tribute: Nina Simone", group: "tribute", blurb: "After-hours spotlight, ivory piano keys, and quiet midnight lounge (palette & mood only)." },
  { id: "theme-host-coffee-house", label: "Coffee House", group: "host", blurb: "Espresso browns, steamed cream, and soft morning café warmth." },
  { id: "theme-host-warm-hearth", label: "Warm Hearth", group: "host", blurb: "Terracotta glow, amber firelight, and cozy brick-room comfort." },
  { id: "theme-host-velvet-lounge", label: "Velvet Lounge", group: "host", blurb: "Deep burgundy velvet, brass accents, and low-lit jazz-club mood." },
  { id: "theme-host-accessible-dark", label: "Accessible Dark", group: "host-accessible", blurb: "High-contrast near-black — sky blue and amber accents, no red/green reliance." },
  { id: "theme-host-accessible-charcoal", label: "Accessible Charcoal", group: "host-accessible", blurb: "Cool charcoal dark mode — cyan and gold accents for strong shape contrast." },
  { id: "theme-host-accessible-light", label: "Accessible Light", group: "host-accessible", blurb: "Bright dashboard — colour-blind-safe blue and orange on white." },
];

const VALID_THEME_IDS = new Set(THEME_OPTIONS.map(theme => theme.id));
const HOST_THEME_IDS = new Set(
  THEME_OPTIONS.filter(theme => theme.group === "host" || theme.group === "host-accessible").map(theme => theme.id)
);

export function normalizeThemeId(themeId) {
  return VALID_THEME_IDS.has(themeId) ? themeId : DEFAULT_THEME;
}

export function normalizeHostThemeId(themeId) {
  return HOST_THEME_IDS.has(themeId) ? themeId : DEFAULT_HOST_THEME;
}

export function resolveUserThemeName(user) {
  if (!user) return DEFAULT_THEME;
  if (user.is_host) return normalizeHostThemeId(user.theme_name);
  return normalizeThemeId(user.theme_name);
}

/**
 * Theme for app chrome (nav, listen, home, profile, etc.).
 * Hosts use a personal dashboard theme only they see.
 * Fans use profile theme; artists use studio theme when editing the app.
 */
export function resolvePersonalAppTheme(user, artistProfile = null) {
  if (!user) return DEFAULT_THEME;
  if (user.is_host) return normalizeHostThemeId(user.theme_name);
  if (user.is_artist) {
    return normalizeThemeId(artistProfile?.studio_theme_name);
  }
  return resolveUserThemeName(user);
}

/**
 * True when the user is browsing someone else's public artist page.
 */
export function isOtherArtistProfile(currentUser, selectedArtist, { previewAsFan = false } = {}) {
  if (!selectedArtist) return false;
  if (!currentUser) return true;
  if (previewAsFan && currentUser.username === selectedArtist.owner_username) return false;
  return selectedArtist.owner_username !== currentUser.username;
}

/**
 * Pick the theme class for an artist profile shell.
 * Owners see their studio theme unless previewing as a fan.
 */
export function resolveArtistThemeName(artist, { isOwner = false, previewAsFan = false } = {}) {
  if (!artist) return DEFAULT_THEME;
  const raw = isOwner && !previewAsFan ? artist.studio_theme_name : artist.theme_name;
  return normalizeThemeId(raw);
}

export function getThemeOption(themeId) {
  return THEME_OPTIONS.find(theme => theme.id === themeId) || THEME_OPTIONS[0];
}

export function groupThemeOptions() {
  return {
    accessible: THEME_OPTIONS.filter(theme => theme.group === "accessible"),
    platform: THEME_OPTIONS.filter(theme => theme.group === "platform"),
    tribute: THEME_OPTIONS.filter(theme => theme.group === "tribute"),
    host: THEME_OPTIONS.filter(theme => theme.group === "host"),
    hostAccessible: THEME_OPTIONS.filter(theme => theme.group === "host-accessible"),
  };
}

export function groupThemeOptionsForVariant(variant = "fan") {
  const groups = groupThemeOptions();
  if (variant === "host") {
    return {
      hostAccessible: groups.hostAccessible,
      host: groups.host,
    };
  }
  return {
    accessible: groups.accessible,
    platform: groups.platform,
    tribute: groups.tribute,
  };
}
