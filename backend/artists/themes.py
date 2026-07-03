DEFAULT_THEME = "theme-indie-dark"
DEFAULT_HOST_THEME = "theme-host-warm-hearth"

# Display labels only — tributes evoke mood/palette, never artist assets or likeness.
THEME_CHOICES = [
    (DEFAULT_THEME, "IndieFund Dark"),
    ("theme-retro-vhs", "Retro VHS"),
    ("theme-clean-label", "Clean Label"),
    ("theme-boombap", "Boom Bap"),
    ("theme-neon-club", "Neon Club"),
    ("theme-accessible-dark", "Accessible Dark"),
    ("theme-accessible-light", "Accessible Light"),
    ("theme-tribute-purple-rain", "Tribute: Prince"),
    ("theme-tribute-alien-pop", "Tribute: Oliver Tree"),
    ("theme-tribute-gold-frame", "Tribute: Marvin Gaye"),
    ("theme-tribute-starman", "Tribute: David Bowie"),
    ("theme-tribute-neon-angel", "Tribute: Avicii"),
    ("theme-tribute-midnight-piano", "Tribute: Nina Simone"),
    (DEFAULT_HOST_THEME, "Warm Hearth"),
    ("theme-host-coffee-house", "Coffee House"),
    ("theme-host-velvet-lounge", "Velvet Lounge"),
    ("theme-host-accessible-dark", "Host Accessible Dark"),
    ("theme-host-accessible-charcoal", "Host Accessible Charcoal"),
    ("theme-host-accessible-light", "Host Accessible Light"),
]

VALID_THEME_NAMES = {key for key, _ in THEME_CHOICES}

HOST_THEME_NAMES = {
    "theme-host-coffee-house",
    "theme-host-warm-hearth",
    "theme-host-velvet-lounge",
    "theme-host-accessible-dark",
    "theme-host-accessible-charcoal",
    "theme-host-accessible-light",
}

PUBLIC_THEME_NAMES = VALID_THEME_NAMES - HOST_THEME_NAMES


def normalize_theme_name(value):
    if value in VALID_THEME_NAMES:
        return value
    return DEFAULT_THEME


def normalize_host_theme(value):
    if value in HOST_THEME_NAMES:
        return value
    return DEFAULT_HOST_THEME


def normalize_artist_theme(value):
    theme = normalize_theme_name(value)
    if theme in HOST_THEME_NAMES:
        return DEFAULT_THEME
    return theme


def normalize_profile_theme(value, user_type=None):
    if user_type == "host":
        return normalize_host_theme(value)
    theme = normalize_theme_name(value)
    if theme in HOST_THEME_NAMES:
        return DEFAULT_THEME
    return theme
