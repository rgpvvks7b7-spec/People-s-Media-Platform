import privacyPolicySupplement from "../../../legal/privacy-policy-supplement.md?raw";
import cookiePolicySupplement from "../../../legal/cookie-policy-supplement.md?raw";
import privacyPolicy from "../../../legal/privacy-policy.md?raw";
import termsOfService from "../../../legal/terms-of-service.md?raw";
import communityGuidelines from "../../../legal/community-guidelines.md?raw";
import copyrightPolicy from "../../../legal/copyright-policy.md?raw";
import artistAgreement from "../../../legal/artist-agreement.md?raw";
import fanAgreement from "../../../legal/fan-agreement.md?raw";
import cookiePolicy from "../../../legal/cookie-policy.md?raw";

export const LEGAL_PAGES = {
  privacy: {
    id: "privacy",
    title: "Privacy Policy",
    description: "How IndieFund collects, uses, and protects your personal information.",
    effectiveDate: "28 June 2026",
    content: privacyPolicy,
    supplement: privacyPolicySupplement,
    iubendaEmbed: "privacy-policy",
  },
  terms: {
    id: "terms",
    title: "Terms of Service",
    description: "The main agreement governing your use of IndieFund.",
    effectiveDate: "28 June 2026",
    content: termsOfService,
  },
  "community-guidelines": {
    id: "community-guidelines",
    title: "Community Guidelines",
    description: "Acceptable behaviour for artists, fans, and hosts on IndieFund.",
    effectiveDate: "28 June 2026",
    content: communityGuidelines,
  },
  copyright: {
    id: "copyright",
    title: "Copyright Policy",
    description: "How to report copyright infringement and our takedown process.",
    effectiveDate: "28 June 2026",
    content: copyrightPolicy,
  },
  "artist-agreement": {
    id: "artist-agreement",
    title: "Artist Agreement",
    description: "Terms for artists uploading content and receiving fan support.",
    effectiveDate: "28 June 2026",
    content: artistAgreement,
  },
  "fan-agreement": {
    id: "fan-agreement",
    title: "Fan Agreement",
    description: "Terms for fans supporting artists through subscriptions and purchases.",
    effectiveDate: "28 June 2026",
    content: fanAgreement,
  },
  cookies: {
    id: "cookies",
    title: "Cookie Policy",
    description: "How IndieFund uses cookies and similar technologies.",
    effectiveDate: "28 June 2026",
    content: cookiePolicy,
    supplement: cookiePolicySupplement,
    iubendaEmbed: "cookie-policy",
  },
};

export const LEGAL_PAGE_SUPPLEMENTS = {
  privacy: privacyPolicySupplement,
  cookies: cookiePolicySupplement,
};

export const LEGAL_PAGE_IDS = new Set(Object.keys(LEGAL_PAGES));

export const LEGAL_FOOTER_LINKS = [
  { page: "privacy", label: "Privacy" },
  { page: "terms", label: "Terms" },
  { page: "community-guidelines", label: "Community Guidelines" },
  { page: "copyright", label: "Copyright" },
];

export function getLegalPage(pageId) {
  return LEGAL_PAGES[pageId] || null;
}
