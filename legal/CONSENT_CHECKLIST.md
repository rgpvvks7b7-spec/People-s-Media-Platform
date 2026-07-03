# Cookie & consent checklist (AU / EU basics)

Use before collecting real emails (waitlist, registration) on production or staging.

## Before early signup (Phase 5)

- [ ] **Privacy Policy** published at `/?page=privacy` (Iubenda embed or markdown fallback)
- [ ] **Cookie Policy** published at `/?page=cookies`
- [ ] **Iubenda consent banner** configured (`VITE_IUBENDA_SITE_ID`, `VITE_IUBENDA_COOKIE_POLICY_ID`) on staging/production
- [ ] **No advertising cookies** — confirm Iubenda dashboard has marketing/ad purpose disabled
- [ ] **Waitlist form** requires Privacy Policy acceptance (implemented)
- [ ] **Registration** requires Terms + Privacy acceptance; stores `terms_accepted_at` (implemented)
- [ ] **Fallback notice** shown when Iubenda is not configured (local dev only for real addresses)

## Australia (Privacy Act / APPs)

- [ ] Collection notice covers email, city, and optional genres on waitlist
- [ ] Privacy contact published (`privacy@indiefund.com` in policies)
- [ ] Overseas disclosure noted (Stripe US) in Privacy Policy supplement
- [ ] Unsubscribe / opt-out path documented for marketing emails (waitlist launch email in Phase 6)

## EU / UK (GDPR-style, if you serve those users)

- [ ] Lawful basis documented: consent for waitlist; contract for account registration
- [ ] Iubenda `countryDetection: true` enabled (implemented in `iubenda.js`)
- [ ] Strictly necessary cookies documented (session, CSRF, Stripe checkout)
- [ ] No non-essential cookies load before consent

## Engineering verification

```bash
# Staging SMTP
cd backend && python manage.py test_transactional_email --to=you@example.com

# Production config
cd backend && python manage.py beta_security_check --strict
```

## Local development

When Iubenda env vars are unset, the app shows a **strictly necessary cookies only** fallback banner and markdown legal pages. Do not point real users at localhost for waitlist collection.
