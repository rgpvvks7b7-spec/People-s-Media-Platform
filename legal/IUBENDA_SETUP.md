# Iubenda Setup Guide — IndieFund

Use this checklist after creating your [Iubenda](https://www.iubenda.com) account. Copy values into `frontend/.env.local` (never commit real IDs to git).

---

## 1. Create account and site

1. Sign up at [iubenda.com](https://www.iubenda.com)
2. Add a **Website** project named **IndieFund**
3. Recommended plan: **Essentials** (~€4.99/mo) — Privacy + Cookie Policy, cookie scanner, consent banner

---

## 2. Privacy Policy questionnaire

**Business type:** Online platform / marketplace / SaaS with user accounts and payments

**Answer YES — data collected:**

- Account registration (username, email, display name, city, genres, avatar, bio)
- User-generated content (music, posts, live streams, images)
- Payment processing via **Stripe** (card data handled by Stripe, not stored by IndieFund)
- First-party server-side usage analytics (page views, plays, purchases — not ad networks)
- Optional web push notification subscriptions
- Fan email sharing opt-in (shared with artists only when opted in)
- Host/venue contact details for IndieFund | Spaces

**Answer NO — never used:**

- **Advertising cookies / remarketing / ad pixels**
- **Sale of personal data**
- Meta Pixel, Google Ads, TikTok Pixel, or similar

**Third-party services to disclose:**

- Stripe (payments, Connect payouts)
- Email delivery provider
- Cloud hosting / infrastructure
- Social embeds (Instagram, TikTok, YouTube — when user interacts)

**Jurisdiction:** Australia primary; enable **GDPR / international** clauses for global users

After generation, copy the **Privacy Policy ID** → `VITE_IUBENDA_PRIVACY_POLICY_ID`

---

## 3. Cookie Policy questionnaire

**Cookies in use today:**

| Type | Examples | Consent needed |
|------|----------|----------------|
| Strictly necessary | Django session, CSRF (`csrftoken`) | No |
| Functional | Local storage (cart, player prefs, UI state) | Inform only |
| Analytics | **None today** | N/A |
| Marketing / advertising | **None — never** | N/A |

**Important answers:**

- Do you use advertising cookies? **NO — never**
- Do you use remarketing? **NO**
- Third-party analytics today? **NO** (may add later with consent only)

Copy the **Cookie Policy ID** → `VITE_IUBENDA_COOKIE_POLICY_ID`

---

## 4. Cookie banner configuration

Open **Privacy Controls and Cookie Solution** → Configure:

| Setting | Value |
|---------|-------|
| Marketing / advertising purpose | **Disabled — do not enable** |
| Analytics purpose | Enable category in dashboard but **attach no scripts** until needed |
| Google Consent Mode ad signals | **Off** |
| Prior blocking | On (blocks scripts until consent when analytics added) |
| Banner style | Informational / minimal (essential cookies only today) |
| Cookie policy link | Use Iubenda-generated policy or `/?page=cookies` |

See [IUBENDA_BANNER_CONFIG.md](./IUBENDA_BANNER_CONFIG.md) for detailed dashboard settings.

Copy **Site ID** → `VITE_IUBENDA_SITE_ID`

---

## 5. Environment variables

```bash
# frontend/.env.local
VITE_IUBENDA_SITE_ID=1234567
VITE_IUBENDA_COOKIE_POLICY_ID=8901234
VITE_IUBENDA_PRIVACY_POLICY_ID=5678901
```

Restart the Vite dev server after adding variables.

When unset, IndieFund falls back to markdown legal drafts in `legal/*.md`.

---

## 6. Cookie scanner (staging)

1. Deploy staging build with env vars set
2. Run Iubenda **Cookie Scanner** against your staging URL
3. Expected detections: session cookie, CSRF, Stripe checkout embeds, optional social embeds
4. **Should NOT detect:** Meta Pixel, Google Ads, analytics tags (none installed)

---

## 7. Merge platform-specific clauses

Iubenda generates base Privacy/Cookie policies. IndieFund-specific sections stay in:

- [privacy-policy-supplement.md](./privacy-policy-supplement.md) — shown below Iubenda embed on `/?page=privacy`
- [cookie-policy-supplement.md](./cookie-policy-supplement.md) — shown below Iubenda embed on `/?page=cookies`

Also copy key IndieFund clauses into your Iubenda policy editor (Stripe, journey analytics, email opt-in, no ad cookies pledge).

Custom docs **stay in repo** (not Iubenda): Terms, Artist Agreement, Fan Agreement, Copyright, Community Guidelines.

---

## 8. Phase 3

Australian lawyer review still required before significant revenue — see [README.md](./README.md).
