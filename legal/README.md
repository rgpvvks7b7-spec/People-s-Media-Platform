# IndieFund Legal Documents

**Status:** Phase 4 code-ready — lawyer review + Iubenda account setup still required before revenue  
**Effective date:** 28 June 2026  
**Last updated:** 29 June 2026

> Replace all `[placeholder]` values before launch. Have an Australian technology lawyer review everything in Phase 3.

---

## Entity details (fill in before launch)

| Field | Value |
|-------|-------|
| Legal entity name | `[Legal Entity Name]` |
| ABN | `[ABN]` |
| Registered address | `[Registered Business Address]` |
| Legal contact | legal@indiefund.com |
| Privacy contact | privacy@indiefund.com |
| Copyright contact | copyright@indiefund.com |
| Governing law | Victoria, Australia |

---

## Document index

| Document | File | Platform page | Source |
|----------|------|---------------|--------|
| Privacy Policy | [privacy-policy.md](./privacy-policy.md) + [supplement](./privacy-policy-supplement.md) | `/?page=privacy` | Iubenda embed when configured; markdown fallback |
| Terms of Service | [terms-of-service.md](./terms-of-service.md) | `/?page=terms` | Custom (Phase 1) |
| Community Guidelines | [community-guidelines.md](./community-guidelines.md) | `/?page=community-guidelines` | Custom (Phase 1) |
| Copyright Policy | [copyright-policy.md](./copyright-policy.md) | `/?page=copyright` | Custom (Phase 1) |
| Artist Agreement | [artist-agreement.md](./artist-agreement.md) | `/?page=artist-agreement` | Custom (Phase 1) |
| Fan Agreement | [fan-agreement.md](./fan-agreement.md) | `/?page=fan-agreement` | Custom (Phase 1) |
| Cookie Policy | [cookie-policy.md](./cookie-policy.md) + [supplement](./cookie-policy-supplement.md) | `/?page=cookies` | Iubenda embed when configured; markdown fallback |

---

## Phase 2 — Iubenda (chosen)

**Vendor:** [Iubenda](https://www.iubenda.com) — not Termly or TermsFeed.

Setup guides:

- [IUBENDA_SETUP.md](./IUBENDA_SETUP.md) — account, questionnaire answers, env vars
- [IUBENDA_BANNER_CONFIG.md](./IUBENDA_BANNER_CONFIG.md) — banner dashboard settings

### Cookie policy (hard rules)

| Rule | Status |
|------|--------|
| Advertising cookies | **Never** — Meta Pixel, Google Ads, remarketing, ad networks banned |
| Third-party analytics today | **None** — first-party server-side journey data only |
| Analytics in future | Consent-gated via Iubenda only; prior blocking required |
| Discovery Ads | First-party promotions — not ad network cookies |

### Environment variables

Set in `frontend/.env.local` (see [frontend/.env.example](../frontend/.env.example)):

```
VITE_IUBENDA_SITE_ID=
VITE_IUBENDA_COOKIE_POLICY_ID=
VITE_IUBENDA_PRIVACY_POLICY_ID=
```

When unset, the app uses markdown drafts and no consent banner (local dev default).

### What Iubenda generates vs custom docs

| Iubenda | Custom (keep in repo) |
|---------|----------------------|
| Privacy Policy base | Terms of Service |
| Cookie Policy base | Artist Agreement |
| Cookie consent banner | Fan Agreement |
| | Copyright Policy |
| | Community Guidelines |
| Platform supplements | [privacy-policy-supplement.md](./privacy-policy-supplement.md), [cookie-policy-supplement.md](./cookie-policy-supplement.md) |

---

## Engineering guardrails

**Banned without explicit legal review and user consent infrastructure:**

- Meta Pixel / Facebook Pixel
- Google Ads / gtag ad conversion tags
- TikTok Pixel
- Twitter/X advertising tags
- Criteo, Taboola, Outbrain, or similar ad networks
- Any remarketing or cross-site ad tracking SDK

**Allowed patterns:**

- First-party server-side analytics (`FanJourneyEvent` — already implemented)
- Stripe checkout (payment processor cookies)
- Social embeds when user interacts (disclosed in Cookie Policy)
- Third-party analytics **only** if added through Iubenda consent with prior blocking — never advertising

**PR checklist:** Before merging any marketing/analytics script, confirm it is wrapped in Iubenda auto-blocking and is not an advertising cookie.

---

## Platform features reflected in these drafts

- **User types:** fan, artist, host
- **Payments:** Stripe Checkout, Connect Express, Billing Portal
- **Platform fees:** 10% support (5% on paid plans); 0% tips; 15% marketplace/commissions (12% on Studio); 15% tickets
- **Content:** music uploads, posts, Instants, live streams, store, commissions, tickets
- **AI policy:** disclosure required; fully AI-generated music prohibited
- **Email sharing:** opt-in only, global and per-artist revocation
- **Discovery Ads:** $5–$100 budget cap, engagement-based billing (not ad cookies)
- **Artist plans:** Pro $12/mo, Studio $29/mo
- **Venue hosts:** F&B revenue excluded from platform fees
- **Beta status:** features and payment modes may change

Source of truth for fees: [`backend/config/platform_fees.py`](../backend/config/platform_fees.py)

---

## Phase 3 — Lawyer review checklist

Have an **Australian technology lawyer** review before handling significant revenue or large user volumes.

### Priority items

- [ ] **Australian Consumer Law** — refund rights for digital goods, subscriptions, and event tickets
- [ ] **Privacy Act / APPs** — collection notices, overseas transfers (Stripe US), retention periods
- [ ] **Iubenda + AU law** — confirm generated GDPR/international clauses fit AU-primary platform
- [ ] **Copyright** — Australian notice-and-takedown vs US DMCA safe harbour if serving US users
- [ ] **GST / tax** — marketplace facilitator obligations, artist income reporting
- [ ] **Stripe** — incorporation of Stripe Connected Account Agreement and Terms of Service
- [ ] **Host/venue liability** — ticketed events, booking disputes, F&B representations
- [ ] **Beta transition** — updating terms when exiting beta / enabling production payments
- [ ] **Entity placeholders** — replace all `[Legal Entity Name]`, `[ABN]`, `[Registered Business Address]`
- [ ] **Children** — age threshold (currently 16 in drafts)
- [ ] **Liability caps** — enforceability under ACL
- [ ] **No advertising cookies** — confirm pledge is enforceable in final policies

### Deferred documents (create after core review)

- Refund Policy (standalone)
- Acceptable Use Policy
- Creator Monetization Policy
- AI Content Policy (standalone)
- Trust & Safety Policy
- Trademark Policy
- Payment & Payout Policy
- Account Verification Policy
- Data Retention Policy
- Security Policy
- Accessibility Statement

---

## Maintenance workflow

1. **Build the platform** — features drive policy updates
2. **Update markdown supplements** when IndieFund-specific behavior changes
3. **Sync Iubenda** Privacy/Cookie policies when data collection changes
4. **Never enable** marketing/advertising purpose in Iubenda dashboard
5. **Lawyer review** a few weeks before public launch — see [CONSENT_CHECKLIST.md](./CONSENT_CHECKLIST.md)
6. **Version bump** effective dates when publishing changes; notify users of material updates

---

## Registration consent

Users must accept the Terms of Service and Privacy Policy at registration. Acceptance timestamp is stored on the user record as `terms_accepted_at`.
