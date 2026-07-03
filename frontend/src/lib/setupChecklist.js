export function getSetupDismissKey(userId, role) {
  return `indiefundSetupDismissed:${role}:${userId}`;
}

export function isSetupDismissed(userId, role) {
  if (!userId || !role) return false;
  try {
    return window.localStorage.getItem(getSetupDismissKey(userId, role)) === "true";
  } catch {
    return false;
  }
}

export function dismissSetup(userId, role) {
  if (!userId || !role) return;
  try {
    window.localStorage.setItem(getSetupDismissKey(userId, role), "true");
  } catch {
    // ignore storage failures
  }
}

export function markInviteLinkShared(userId) {
  if (!userId) return;
  try {
    window.localStorage.setItem(`indiefundInviteShared:${userId}`, "true");
  } catch {
    // ignore storage failures
  }
}

export function hasSharedInviteLink(userId, referrals) {
  if (!userId) return false;
  try {
    if (window.localStorage.getItem(`indiefundInviteShared:${userId}`) === "true") return true;
  } catch {
    // ignore storage failures
  }
  return Number(referrals?.invite_follows || 0) > 0
    || Number(referrals?.invite_subscribers || 0) > 0;
}

export function markPreviewedPublicPage(userId) {
  if (!userId) return;
  try {
    window.localStorage.setItem(`indiefundPublicPreview:${userId}`, "true");
  } catch {
    // ignore storage failures
  }
}

export function hasPreviewedPublicPage(userId) {
  if (!userId) return false;
  try {
    return window.localStorage.getItem(`indiefundPublicPreview:${userId}`) === "true";
  } catch {
    return false;
  }
}

export function getChecklistProgress(items) {
  const total = items.length;
  const doneCount = items.filter(item => item.done).length;
  return {
    doneCount,
    total,
    complete: total > 0 && doneCount === total,
    percent: total ? Math.round((doneCount / total) * 100) : 0,
  };
}

export function getNextChecklistItem(items) {
  return items.find(item => !item.done) || null;
}

export function getFirstIncompleteChallenge(challengeBoard) {
  if (!challengeBoard) return null;
  const combined = [...(challengeBoard.daily || []), ...(challengeBoard.weekly || [])];
  return combined.find(item => !item.completed) || null;
}
