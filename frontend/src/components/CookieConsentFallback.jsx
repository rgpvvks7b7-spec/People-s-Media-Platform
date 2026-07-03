import { useEffect, useState } from "react";

const DISMISS_KEY = "indiefundCookieNoticeDismissed";

export function CookieConsentFallback({ onOpenCookies }) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    try {
      setVisible(window.localStorage.getItem(DISMISS_KEY) !== "true");
    } catch {
      setVisible(true);
    }
  }, []);

  if (!visible) return null;

  function dismiss() {
    try {
      window.localStorage.setItem(DISMISS_KEY, "true");
    } catch {
      // ignore storage failures
    }
    setVisible(false);
  }

  return (
    <aside className="cookie-consent-fallback" role="region" aria-label="Cookie notice">
      <p>
        IndieFund uses strictly necessary cookies (session and CSRF) to keep you signed in and secure checkout.
        We do not use advertising cookies.
      </p>
      <div className="cookie-consent-fallback-actions">
        <button type="button" className="secondary compact" onClick={onOpenCookies}>
          Cookie Policy
        </button>
        <button type="button" className="primary compact" onClick={dismiss}>
          OK
        </button>
      </div>
    </aside>
  );
}
