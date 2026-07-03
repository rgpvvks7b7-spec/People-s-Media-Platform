import { useEffect } from "react";
import { isIubendaConsentConfigured, loadIubendaConsentScript } from "../lib/iubenda.js";

export function IubendaConsent() {
  useEffect(() => {
    if (!isIubendaConsentConfigured()) {
      return undefined;
    }

    let cancelled = false;

    loadIubendaConsentScript().catch(() => {
      if (!cancelled) {
        console.warn("IndieFund: Iubenda consent script failed to load.");
      }
    });

    return () => {
      cancelled = true;
    };
  }, []);

  return null;
}
