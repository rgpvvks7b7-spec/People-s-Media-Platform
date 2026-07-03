import { isIubendaConsentConfigured } from "./iubenda.js";

export const LEGAL_EFFECTIVE_DATE = "28 June 2026";

export function isLegalPreRelease() {
  const flag = (import.meta.env.VITE_LEGAL_PRE_RELEASE || "true").trim().toLowerCase();
  return flag !== "false" && flag !== "0";
}

export function getLegalFooterNote() {
  if (isIubendaConsentConfigured()) {
    return isLegalPreRelease()
      ? `Pre-release · Effective ${LEGAL_EFFECTIVE_DATE} · Iubenda-managed consent`
      : `Effective ${LEGAL_EFFECTIVE_DATE}`;
  }
  return isLegalPreRelease()
    ? `Pre-release policies · Effective ${LEGAL_EFFECTIVE_DATE}`
    : `Effective ${LEGAL_EFFECTIVE_DATE}`;
}

export function getLegalPageBadge() {
  if (!isLegalPreRelease()) return null;
  return "Pre-release";
}
