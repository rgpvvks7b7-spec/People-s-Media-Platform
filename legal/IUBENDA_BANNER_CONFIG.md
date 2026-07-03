# Iubenda Banner Configuration — IndieFund

Dashboard settings for **Privacy Controls and Cookie Solution**. Configure in Iubenda; changes apply via remote configuration (no code redeploy needed).

---

## Hard product rules

| Rule | Setting |
|------|---------|
| Advertising cookies | **Never enabled** — no marketing purpose in banner |
| Remarketing / ad pixels | **Never** — banned in engineering (see README) |
| Third-party analytics today | **None loaded** |
| Analytics in future | Consent-gated via Iubenda only; add scripts through Iubenda auto-blocking |

---

## Recommended dashboard settings

### Purposes / categories

| Purpose | Dashboard | Scripts attached |
|---------|-----------|------------------|
| Necessary | Enabled | Session + CSRF (automatic) |
| Functional | Enabled | None (local storage documented in policy) |
| Analytics | Category visible, **default deny** | **Zero scripts today** |
| Marketing | **Disabled / not shown** | **Never** |

### Banner behaviour (essential-only mode)

Until third-party analytics is added:

- **Accept** and **Customize** buttons visible
- **Reject** button visible (GDPR-friendly)
- Do **not** show marketing toggle
- Analytics toggle may appear but has no scripts behind it
- Link to Cookie Policy: `/?page=cookies` or Iubenda-hosted policy

### Advanced — disable permanently

- Google Consent Mode: **do not enable ad_storage or ad_personalization**
- IAB TCF: not required unless running programmatic ads (IndieFund does not)
- US state laws module: optional; enable if targeting US users

### Remote configuration

Enable **remote configuration** so banner and policy updates apply without re-embedding code.

---

## When adding analytics later

1. Add script in Iubenda dashboard under **Analytics** purpose only
2. Enable Iubenda **prior blocking** so script loads only after opt-in
3. Update Privacy + Cookie policies in Iubenda
4. **Do not** enable marketing category
5. Run cookie scanner again to verify

---

## Verification checklist

- [ ] Banner appears on staging with env vars set
- [ ] No "Marketing" or "Advertising" purpose in customize panel
- [ ] Cookie scanner finds no ad/analytics pixels
- [ ] `/?page=privacy` shows Iubenda embed + IndieFund supplement
- [ ] `/?page=cookies` shows Iubenda embed + IndieFund supplement
- [ ] Dev without env vars still shows markdown fallback
