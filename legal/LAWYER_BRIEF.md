# IndieFund — Lawyer Briefing Pack

**Purpose:** A scoping brief to hand to an Australian technology lawyer so they can advise efficiently.
**Scope:** AU-primary legal entity, **global launch** (users in AU, US, EU/UK and elsewhere from day one).
**Status:** Pre-launch. Draft policies exist in [`legal/`](./README.md) and need review, not a rewrite.
**Last updated:** 30 June 2026

> **This is not legal advice.** It is a founder-prepared briefing to make professional review faster and cheaper. Nothing here should be relied on as a legal conclusion.

---

## 1. Product summary

IndieFund is a multi-sided marketplace that helps independent artists earn from real fans through subscriptions, tips, merch/music sales, commissions, and local live shows — with discovery designed to avoid pay-to-win virality.

**User types**
- **Fan** — discovers and supports artists; subscribes, tips, buys, attends shows.
- **Artist** — profile, content, sales, payouts.
- **Host** — venue that lists spaces, manages bookings, and sells show tickets.

**Money flows (every way value moves)**
- Monthly support / subscriptions to artists (min $1/mo; fan cap of 50 artists with paid extension planned).
- One-time tips.
- Marketplace sales (music + merch, digital and physical).
- Custom commissions (artist does paid bespoke work).
- Event tickets, with artist/venue **door splits** (percentage or flat-fee deals); F&B revenue stays with the host.
- **Fan discovery credits** — fans *earn* credits for genuine discovery engagement and *redeem* them against tips/purchases (a stored-value-like feature; see §3.1).
- **Discovery Ads** — first-party promoted releases, capped $5–$100 per campaign, billed per qualified engagement (not impressions, not ad-network cookies).
- **Creator plans** — Artist Pro $12/mo, Studio $29/mo (Studio includes $25/mo promotion credits).

**Platform take rate** (single source of truth: [`backend/config/platform_fees.py`](../backend/config/platform_fees.py))
- 10% on support/subscriptions (5% on Artist Pro and Studio plans).
- 0% on tips (all plans).
- 15% on marketplace sales and commissions (12% on the Studio plan); 15% on event tickets (all plans).

**Payments architecture**
- Stripe Checkout (purchases), Stripe Connect Express (payouts to artists/hosts), Stripe Billing Portal (subscription management). See [`STRIPE_SETUP.md`](../STRIPE_SETUP.md).

**Content & trust**
- User-generated content: music uploads, posts, "Instants", live streaming, stories.
- AI policy: disclosure required; fully AI-generated music prohibited.
- Email sharing / mailing-list export is opt-in; consent timestamp stored as `email_share_consent_at` ([`backend/accounts/models.py`](../backend/accounts/models.py)).
- First-party server-side analytics only (`FanJourneyEvent`); **no advertising cookies** ever — see [`.cursor/rules/privacy-cookies.mdc`](../.cursor/rules/privacy-cookies.mdc).
- Age threshold currently 16; governing law set to Victoria, Australia.

---

## 2. How to read this brief

Each question below is tied to a concrete feature already in the product, so the lawyer can give specific answers. Priorities are ordered: financial-services exposure first, because it can change the entire structure.

---

## 3. Prioritized legal questions

### 3.1 Financial services & money movement (highest priority)
- Does collecting funds, briefly holding them, and splitting them between artist/venue/platform make IndieFund a **payment facilitator / money transmitter** needing an **AFSL** or other authorisation — or does Stripe Connect's model (Stripe as merchant of record / regulated processor) keep us outside that perimeter? Get this in writing.
- **Fan discovery credits**: are earned-and-redeemable credits a **non-cash payment facility / stored value**, triggering financial-services regulation (AU) and equivalents abroad? Same question for Discovery Ad / Studio promotion credits.
- Who is **merchant of record** for each flow, who legally holds funds during commissions/ticketing (escrow?), and what are our **refund and chargeback** liabilities?
- Cross-border money movement (global users + AU entity + US-based Stripe): any additional licensing or registration in major markets (US state money-transmitter laws, EU/UK e-money)?
- How must Stripe's Connected Account Agreement and ToS be incorporated into our Artist/Host agreements?

### 3.2 Australian Consumer Law (ACL) — and global consumer overlay
- Consumer-guarantee and refund rights for digital goods, subscriptions, commissions, and event tickets.
- Subscription practices: cancellation, auto-renewal disclosure, the 50-artist cap and "extend your limit" upsell.
- Enforceability of our **liability caps / disclaimers / indemnities** under ACL non-excludable guarantees ([`legal/terms-of-service.md`](./terms-of-service.md)).
- Are "beta / features may change" disclaimers effective?
- Global overlay: EU/UK consumer law (e.g. 14-day withdrawal rights for digital content), US state consumer-protection and auto-renewal laws.

### 3.3 Privacy & data protection (global)
- **Australia:** Privacy Act / APPs — collection notices, our Privacy Policy ([`legal/privacy-policy.md`](./privacy-policy.md) + [supplement](./privacy-policy-supplement.md)), overseas-transfer disclosures (Stripe/US hosting), retention and deletion.
- **EU/UK GDPR:** lawful basis, data subject rights, international transfer mechanism (SCCs), DPO/EU representative need, breach notification.
- **US state privacy laws** (CCPA/CPRA and successors): consumer rights, "do not sell/share" (we don't sell — confirm), opt-out signals.
- The **email-sharing / mailing-list export** feature: quality of consent and what obligations transfer to artists who receive fan data (artist as a separate controller?).
- Confirm the **no-advertising-cookie** pledge and Iubenda consent setup ([`legal/IUBENDA_SETUP.md`](./IUBENDA_SETUP.md)) are enforceable and sufficient.

### 3.4 Content, IP & copyright (global)
- Takedown regime: AU copyright vs **US DMCA safe harbour** (designated agent, repeat-infringer policy) and EU obligations, since we serve all three. Review [`legal/copyright-policy.md`](./copyright-policy.md).
- Music licensing/royalties: artist warranties of ownership/licence; cover songs, samples; exposure to **APRA AMCOS** and overseas collecting societies.
- Our platform licence to host, stream, and display user content (scope, sublicensing, survival).
- AI-content rules: disclosure requirement and the prohibition on fully AI-generated music — enforceable and clearly drafted?

### 3.5 Trust, safety & online-content law (global)
- Australia's **Online Safety Act** / eSafety obligations (illegal and harmful content, complaints handling, takedown timelines).
- Equivalent duties abroad: **EU Digital Services Act**, UK Online Safety Act.
- Live-streaming moderation duties and incident response.
- Fairness of account suspension/termination and Community Guidelines enforcement ([`legal/community-guidelines.md`](./community-guidelines.md)).

### 3.6 Tax (global)
- AU **GST** registration and any **electronic distribution platform / marketplace operator** obligations on facilitated sales.
- International indirect tax: **EU/UK VAT** on digital services (MOSS/IOSS), **US sales tax** nexus on facilitated marketplace sales.
- Whether we have any **withholding or income-reporting** duties for artist/host payouts (AU and foreign creators).

### 3.7 Venues, events & liability
- Ticketed live shows: cancellation/refund policy, allocation of liability between host, artist, and platform.
- Public-liability insurance expectations and the F&B carve-out.
- Door-split agreements and booking-dispute resolution.

### 3.8 Corporate, entity & brand
- Right structure (e.g. Pty Ltd) and completing entity placeholders in [`legal/README.md`](./README.md): legal entity name, ABN, registered address.
- Trademark protection for "IndieFund" (AU + key markets) and domain/brand clearance.

### 3.9 Minors
- Is **16** the right minimum given global reach, payments, live streaming, and content? Implications for parental consent and heightened privacy duties for under-18s (e.g. GDPR-K, US COPPA for under-13s, AU children's privacy expectations).

---

## 4. Materials to provide to the lawyer

Hand these over as a single pack:

- [ ] **This brief** (`legal/LAWYER_BRIEF.md`) plus the product context in [`PROJECT_BLUEPRINT.md`](../PROJECT_BLUEPRINT.md) and [`ROADMAP.md`](../ROADMAP.md).
- [ ] **Draft policies for review** (mark as drafts): [terms](./terms-of-service.md), [privacy](./privacy-policy.md) + [supplement](./privacy-policy-supplement.md), [cookies](./cookie-policy.md) + [supplement](./cookie-policy-supplement.md), [community guidelines](./community-guidelines.md), [copyright](./copyright-policy.md), [artist agreement](./artist-agreement.md), [fan agreement](./fan-agreement.md).
- [ ] **Fee / money model**: [`backend/config/platform_fees.py`](../backend/config/platform_fees.py) or a plain-English summary of take rates, ticket/door splits, and credits.
- [ ] **Payment & fund-flow description**: Stripe Checkout + Connect Express + Billing Portal, who holds funds, payout timing, merchant-of-record per flow ([`STRIPE_SETUP.md`](../STRIPE_SETUP.md)) and links to Stripe's Connected Account Agreement.
- [ ] **Data inventory & sub-processors**: personal data collected (emails, profile/cover images, Stripe customer IDs, journey/analytics events, mailing-list opt-ins), storage locations, and third parties (Stripe, Iubenda, hosting).
- [ ] **Fan-credits mechanics**: how they are earned, daily caps, and redemption caps — flagged for the stored-value question.
- [ ] **Compliance pledges**: the no-advertising-cookie rule ([`.cursor/rules/privacy-cookies.mdc`](../.cursor/rules/privacy-cookies.mdc)) and the AI-music prohibition.
- [ ] **Geography scope**: global launch (AU-primary), with US/EU/UK users expected from day one.
- [ ] **Intended entity details** (or a request for help forming the entity).

---

## 5. Open decisions for the founder

- Fill entity placeholders in [`legal/README.md`](./README.md): legal entity name, ABN, registered address.
- Confirm which markets actually open at launch (this changes DMCA/GDPR/VAT/sales-tax scope).
- Confirm fund-flow ownership: are we comfortable that Stripe Connect keeps us out of the money-transmission perimeter, or do we need to restructure flows?
- Decide minimum-age policy for a global, payment-enabled, live product.
- Decide whether fan credits stay as a redeemable balance or are reframed (e.g. non-redeemable perks) to reduce financial-services risk.

---

## 6. Related documents

| Doc | Purpose |
|-----|---------|
| [legal/README.md](./README.md) | Legal program overview + Phase 3 review checklist |
| [legal/CONSENT_CHECKLIST.md](./CONSENT_CHECKLIST.md) | Pre-launch consent steps |
| [legal/IUBENDA_SETUP.md](./IUBENDA_SETUP.md) | Privacy/cookie tooling setup |
| [backend/config/platform_fees.py](../backend/config/platform_fees.py) | Canonical fee/credit/campaign model |
| [STRIPE_SETUP.md](../STRIPE_SETUP.md) | Payments configuration |
| [PROJECT_BLUEPRINT.md](../PROJECT_BLUEPRINT.md) | Original product rules |

---

## 7. Machine-readable summary

A structured snapshot for AI agents and tooling. Human-readable sections above are authoritative if they ever conflict.

```yaml
company:
  name: IndieFund
  country: Australia
  governing_law: Victoria
  launch: Global

payments:
  processor: Stripe
  stripe: true
  merchant_of_record: Stripe
  payouts: Stripe Connect Express
  billing_portal: true
  platform_fees:
    support: 0.10
    tips: 0.10
    marketplace: 0.15
    tickets: 0.15
    commissions: 0.15

features:
  subscriptions: true
  tips: true
  merch: true
  music_sales: true
  commissions: true
  tickets: true
  livestream: true
  fan_credits: true
  discovery_ads: true
  creator_plans: true

legal:
  ai_music_banned: true
  ai_disclosure_required: true
  minimum_age: 16
  advertising_cookies: false
  email_sharing: opt_in
  analytics: first_party_only
  status: pre_launch_draft

review_priorities:
  - financial_services_perimeter
  - australian_consumer_law
  - privacy_global
  - copyright_ip
  - trust_and_safety
  - tax_global
  - venue_event_liability
  - entity_and_trademark
  - minors
```
