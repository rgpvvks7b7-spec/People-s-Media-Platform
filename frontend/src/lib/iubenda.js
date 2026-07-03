export const IUBENDA_SITE_ID = (import.meta.env.VITE_IUBENDA_SITE_ID || "").trim();
export const IUBENDA_COOKIE_POLICY_ID = (import.meta.env.VITE_IUBENDA_COOKIE_POLICY_ID || "").trim();
export const IUBENDA_PRIVACY_POLICY_ID = (import.meta.env.VITE_IUBENDA_PRIVACY_POLICY_ID || "").trim();

export const IUBENDA_POLICY_EMBED_PAGES = {
  privacy: {
    link: "privacy-policy",
    policyId: IUBENDA_PRIVACY_POLICY_ID,
  },
  cookies: {
    link: "cookie-policy",
    policyId: IUBENDA_COOKIE_POLICY_ID,
  },
};

export function isIubendaConsentConfigured() {
  return Boolean(IUBENDA_SITE_ID && IUBENDA_COOKIE_POLICY_ID);
}

export function isIubendaPolicyEmbedConfigured(pageId) {
  const config = IUBENDA_POLICY_EMBED_PAGES[pageId];
  return Boolean(config?.policyId);
}

let iubendaLoaderPromise = null;

export function loadIubendaEmbedScript() {
  if (typeof document === "undefined") {
    return Promise.resolve();
  }
  if (document.querySelector('script[data-indiefund-iubenda-embed="true"]')) {
    return Promise.resolve();
  }
  if (iubendaLoaderPromise) {
    return iubendaLoaderPromise;
  }

  iubendaLoaderPromise = new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = "https://cdn.iubenda.com/iubenda.js";
    script.async = true;
    script.dataset.indiefundIubendaEmbed = "true";
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("Unable to load Iubenda embed script."));
    document.head.appendChild(script);
  });

  return iubendaLoaderPromise;
}

let iubendaConsentPromise = null;

export function loadIubendaConsentScript() {
  if (typeof document === "undefined" || !isIubendaConsentConfigured()) {
    return Promise.resolve();
  }
  if (document.querySelector('script[data-indiefund-iubenda-consent="true"]')) {
    return Promise.resolve();
  }
  if (iubendaConsentPromise) {
    return iubendaConsentPromise;
  }

  iubendaConsentPromise = new Promise((resolve, reject) => {
    window._iub = window._iub || [];
    window._iub.csConfiguration = {
      siteId: Number(IUBENDA_SITE_ID),
      cookiePolicyId: Number(IUBENDA_COOKIE_POLICY_ID),
      lang: "en",
      gdprAppliesGlobally: false,
      countryDetection: true,
      perPurposeConsent: true,
      askConsentAtCookiePolicyUpdate: true,
      banner: {
        acceptButtonDisplay: true,
        customizeButtonDisplay: true,
        rejectButtonDisplay: true,
        position: "float-bottom-center",
      },
    };

    const script = document.createElement("script");
    script.src = "https://cdn.iubenda.com/cs/iubenda_cs.js";
    script.async = true;
    script.charset = "UTF-8";
    script.dataset.indiefundIubendaConsent = "true";
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("Unable to load Iubenda consent script."));
    document.head.appendChild(script);
  });

  return iubendaConsentPromise;
}

export function reloadIubendaEmbeds() {
  if (typeof window !== "undefined" && window.iubenda?.embeds?.reload) {
    window.iubenda.embeds.reload();
  }
}
