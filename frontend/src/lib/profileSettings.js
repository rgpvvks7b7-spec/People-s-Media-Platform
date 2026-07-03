export const SETTINGS_SECTIONS = [
  { id: "tickets", label: "My tickets" },
  { id: "library", label: "Library & support" },
  { id: "activity", label: "Fan activity" },
  { id: "credits", label: "Discovery credits" },
  { id: "email", label: "Email sharing" },
  { id: "discovery", label: "Discovery" },
  { id: "gigs", label: "Local gigs" },
  { id: "push", label: "Push notifications" },
  { id: "social", label: "Social content" },
  { id: "beta", label: "Beta feedback" },
  { id: "host", label: "Host profile" },
];

export function getSettingsSectionsForUser(user) {
  if (!user) return [];

  return SETTINGS_SECTIONS.filter(section => {
    if (section.id === "tickets") return !user.is_host;
    if (section.id === "library") return !user.is_host;
    if (section.id === "credits") return !user.is_artist && !user.is_host;
    if (section.id === "email" || section.id === "discovery" || section.id === "gigs" || section.id === "push" || section.id === "social") {
      return !user.is_host;
    }
    if (section.id === "host") return user.is_host;
    return true;
  });
}

export function resolveSettingsSection(sectionParam = "", user, fallback = "library") {
  const valid = getSettingsSectionsForUser(user).map(section => section.id);
  if (valid.includes(sectionParam)) return sectionParam;
  if (valid.includes(fallback)) return fallback;
  return valid[0] || "activity";
}
