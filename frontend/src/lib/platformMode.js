export const PLATFORM_MODE_LIVE = "live";
export const PLATFORM_MODE_PRELAUNCH = "prelaunch";

export const FAN_GATED_PAGES = new Set([
  "listen",
  "discover",
  "music",
  "saved",
  "stores",
  "my-scene",
  "feed",
  "my-music",
  "radio",
]);

export function normalizePlatformMode(value) {
  return value === PLATFORM_MODE_PRELAUNCH ? PLATFORM_MODE_PRELAUNCH : PLATFORM_MODE_LIVE;
}

export function isPrelaunchMode(mode) {
  return normalizePlatformMode(mode) === PLATFORM_MODE_PRELAUNCH;
}

export function canAccessFanExperience(mode, user) {
  if (!isPrelaunchMode(mode)) return true;
  if (!user) return false;
  return Boolean(user.is_artist || user.is_host);
}

export function fanRegistrationOpen(mode) {
  return !isPrelaunchMode(mode);
}

export function isFanGatedPage(page) {
  return FAN_GATED_PAGES.has(page);
}

export function resolvePageForPlatformMode(page, mode, user) {
  if (!isPrelaunchMode(mode)) return page;
  if (!isFanGatedPage(page)) return page;
  if (canAccessFanExperience(mode, user)) return page;
  return "prelaunch";
}
