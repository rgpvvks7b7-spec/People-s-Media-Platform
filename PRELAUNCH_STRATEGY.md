# Pre-launch strategy & build order

**Platform:** IndieFund  
**Last updated:** 2026-06-29  
**Goal:** Ship a bulletproof platform **without** asking real artists to beta-test. Real artists and hosts join only during **early signup** to build listings and stores before fans arrive on launch day.

---

## Principles

1. **Machines prove readiness** — Django tests, Playwright E2E, `beta_scene_loop`, and `beta_security_check` are the QA team. Staging is the manual click-through environment.
2. **Creators are builders, not testers** — Early signup artists/hosts set up profiles, music, stores, and Spaces. They should not hit broken nav or empty flows.
3. **Fans wait until launch** — During prelaunch, fans see waitlist / coming-soon, not a half-empty Discover experience.
4. **One switch to go live** — `PLATFORM_MODE=prelaunch → live` opens fan registration and public discovery when shelves are stocked.

---

## Audience by phase

| Phase | Artists | Hosts | Fans (public) |
|-------|---------|-------|----------------|
| **0–1** Internal only | Dev / seed accounts | Dev / seed accounts | Closed |
| **2–4** Staging | Full studio access on staging | Full Spaces access on staging | Closed or read-only preview |
| **5** Early signup (production) | Register + full setup | Register + list rooms | Waitlist email only |
| **6** Launch day | Already live — share links | Already live | Register + Discover + support |

---

## Strategic build order

Complete each phase before starting the next. Items within a phase can run in parallel where noted.

### Phase 0 — Hardening foundation (no public URL yet)

**Purpose:** Make the existing product trustworthy in dev/staging without new user-facing scope.

| # | Work | Exit criteria |
|---|------|----------------|
| 0.1 | **CI gate** — run on every change: `python manage.py test`, `beta_scene_loop`, `beta_security_check`, Playwright smoke + prelaunch | ✅ `.github/workflows/ci.yml`; smoke + `prelaunch.spec.js` + `onboarding.spec.js` |
| 0.2 | **Staging environment** — Postgres, S3 media, HTTPS cookies, Stripe test mode ([DEPLOYMENT.md](./DEPLOYMENT.md)) | Staging URL loads; auth + checkout work |
| 0.3 | **E2E expansion** — artist upload/post, host room create, onboarding checklist paths, registration a11y (BUG-004/005) | 🟡 `onboarding.spec.js` done; upload/host/a11y specs still open |
| 0.4 | **Commit & branch hygiene** — feature work on branches; main always deployable to staging | No multi-week dirty working tree |

**Do not:** Invite real creators, run ads, or collect emails until Phase 4 legal minimum is met.

---

### Phase 1 — Platform launch mode (foundation for everything else)

**Purpose:** Encode prelaunch vs live in one place so fan and creator experiences do not fight each other.

| # | Work | Exit criteria |
|---|------|----------------|
| 1.1 | **`PLATFORM_MODE` env** — `prelaunch` \| `live` (backend + `VITE_PLATFORM_MODE` frontend) | ✅ `config/platform_mode.py`, `/api/health/`, `.env.example` files |
| 1.2 | **Fan gates (prelaunch)** — block fan registration; gate Discover, Listen swipe, Stores browse, support checkout | ✅ Backend guards + `PrelaunchFanGate` + nav filtering |
| 1.3 | **Public SEO gates** — sitemap/robots: artist public pages OK for early SEO; fan app shell noindex until live | ✅ `artists/public.py` prelaunch robots/sitemap |
| 1.4 | **Admin / ops flip** — documented env change + smoke script after flip | Runbook in this doc § Launch day |

**Depends on:** Phase 0.2 (staging to test gates).

---

### Phase 2 — Early creator signup & fan waitlist

**Purpose:** Production landing for “get listed before launch” without opening the full fan product.

| # | Work | Exit criteria |
|---|------|----------------|
| 2.1 | **Creator landing page** — hero, value prop, “Artist signup” / “Host signup” CTAs | ✅ `CreatorEarlyAccessLanding` at `/` and `/?page=early-access` |
| 2.2 | **Registration rules** — prelaunch allows `user_type=artist` and `user_type=host` only; fan signup → waitlist form | ✅ API block + AuthPanel waitlist tab |
| 2.3 | **Fan waitlist** — email + city (optional); store in DB; double opt-in if legally required | ✅ `FanWaitlistEntry` model, admin CSV export, confirm endpoint |
| 2.4 | **Post-signup routing** — artist → Home dashboard + launch checklist; host → Spaces + host checklist | ✅ Artist → home; new host → spaces + listing form |

**Depends on:** Phase 1.

---

### Phase 3 — Creator self-serve (zero hand-holding)

**Purpose:** Early signup creators finish setup without support tickets.

| # | Work | Exit criteria |
|---|------|----------------|
| 3.1 | ~~**Launch checklist + next action**~~ | ✅ Shipped — fan + artist + host dashboards |
| 3.2 | **Support tier templates** — one-click $1 / $5 / custom | ✅ `$1 Supporter` / `$5 Member` quick-create in tier editor |
| 3.3 | **Host room wizard** — photos, availability, pricing copy helpers | ✅ `SpaceListingWizard` 5-step flow |
| 3.4 | **Payout setup nudge** — Connect onboarding in growth next-action after launch checklist | ✅ Growth action when tier live + Stripe not connected |
| 3.5 | **Preview as fan** — prompt before sharing invite link | ✅ Preview gate + checklist step 4 requires preview |
| 3.6 | **Launch city seed content** — demo artists/venues in launch city so early creators see a living scene | ✅ `seed_demo --launch-city Melbourne` summary |

**Depends on:** Phase 2 (creators are the users of this phase).

---

### Phase 4 — Legal, email & trust (before any real email)

**Purpose:** Safe to collect real addresses and creator accounts on production.

| # | Work | Exit criteria |
|---|------|----------------|
| 4.1 | **Legal review** — Privacy, Terms, Community Guidelines, Copyright ([legal/](./legal/)) | ✅ Pre-release badge + footer; set `VITE_LEGAL_PRE_RELEASE=false` after lawyer sign-off |
| 4.2 | **Transactional email** — verify, receipt, waitlist confirm ([DEPLOYMENT.md](./DEPLOYMENT.md) SMTP) | ✅ `config/transactional_email.py` + `test_transactional_email` command |
| 4.3 | **Cookie / consent** — if waitlist or analytics need it | ✅ Iubenda + fallback banner; [CONSENT_CHECKLIST.md](./legal/CONSENT_CHECKLIST.md) |
| 4.4 | **Rate limits & abuse** — registration, waitlist, upload throttling verified under load | ✅ Upload throttle + expanded `beta_security_check` |

**Depends on:** Phase 0.2. **Blocks:** Phase 5 public early signup.

---

### Phase 5 — Early signup open (production, prelaunch mode)

**Purpose:** Real artists and hosts build inventory; fans only on waitlist.

| # | Work | Exit criteria |
|---|------|----------------|
| 5.1 | **Deploy production** — `PLATFORM_MODE=prelaunch`, live Stripe test or live keys per policy | Production URL live |
| 5.2 | **Creator marketing** — landing link, social, direct outreach (not “please beta test”) | Messaging: “Reserve your page before launch” |
| 5.3 | **Ops monitoring** — Sentry, error alerts, daily `beta_scene_loop` against prod smoke user | On-call runbook |
| 5.4 | **Creator success metrics** — dashboard: % with profile, upload, tier, listing | Weekly internal review, no user bug-hunt |

**Duration:** Weeks to months — until launch city has enough artists, hosts, and content.

**Do not:** Open fan registration or promote Discover to consumers.

---

### Phase 6 — Launch day

**Purpose:** Flip to full marketplace when shelves are ready.

| # | Work | Exit criteria |
|---|------|----------------|
| 6.1 | **Go-live checklist** — see § Launch day runbook below | All boxes checked |
| 6.2 | **Set `PLATFORM_MODE=live`** | Fan registration + Discover + checkout open |
| 6.3 | **Email waitlist** — “We’re live” with link to Discover / launch city | Send via ESP; unsubscribe honored |
| 6.4 | **Email early creators** — “Share your link”; highlight featured launch artists | Sent same day as 6.3 |
| 6.5 | **Post-launch watch** — 48h elevated monitoring; rollback plan documented | No P0 unresolved > 4h |

---

### Phase 7 — Post-launch (after live)

**Purpose:** Retention and revenue — only after Phase 6.

Prioritize from [ROADMAP.md](./ROADMAP.md) P2:

- Push opt-in + My Scene show alerts  
- Tip prompts at peak moments  
- Discovery ad credits / Studio plan UX  
- Invite funnel analytics  
- Cross-browser E2E, performance budgets  

---

## Launch day runbook

```bash
# 1. Pre-flight (staging, same commit as prod)
cd backend && python manage.py test && python manage.py beta_scene_loop && python manage.py beta_security_check
cd frontend && npm run test:e2e:smoke && npm run test:e2e:checkout

# 2. Verify early creator counts (admin / SQL / internal dashboard)
#    - Artists with public profile + ≥1 upload/post
#    - Artists with ≥1 support tier
#    - Hosts with ≥1 live room

# 3. Flip platform mode
#    PLATFORM_MODE=live  (backend + frontend rebuild)

# 4. Smoke on production
#    - Fan register → Discover → save artist → checkout (test card)
#    - Artist public page loads
#    - Host booking flow

# 5. Send waitlist + creator emails

# 6. Monitor Sentry + support inbox for 48h
```

**Rollback:** Set `PLATFORM_MODE=prelaunch` — fans gated again; creator accounts and content preserved.

---

## Verification commands (recurring)

| Command | When |
|---------|------|
| `cd backend && python manage.py test` | Every PR |
| `cd backend && python manage.py beta_scene_loop` | Pre-deploy |
| `cd backend && python manage.py beta_security_check` | Pre-deploy + prod config |
| `cd frontend && npm run test:e2e:smoke` | Every PR |
| `cd frontend && npm run test:e2e:checkout` | Payment-touching PRs |
| `cd frontend && npm run test:e2e:qa` | Weekly / pre-release |

---

## Explicitly out of scope until launch

- Fan growth gamification (streaks, credits redemption UX)  
- Native apps (Capacitor) — PWA first ([MOBILE_APP.md](./MOBILE_APP.md))  
- New tribute themes or cosmetic polish  
- Asking creators to “report bugs” or join a beta Discord  

---

## Decision log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-06-28 | No real-artist beta testing | Harden with automation; creators join for setup only |
| 2026-06-28 | `PLATFORM_MODE` before marketing | Prevents empty fan experience during early signup |
| 2026-06-28 | Legal + email before Phase 5 | Real accounts and waitlist need compliant policies |
| 2026-06-28 | Launch checklist shipped in Phase 3.1 | Reduces support load during early signup |

---

## Related docs

| Doc | Role |
|-----|------|
| [ROADMAP.md](./ROADMAP.md) | Feature backlog (mostly Phase 7+) |
| [BETA_PHASES.md](./BETA_PHASES.md) | Completed feature phases 1–5 |
| [DEPLOYMENT.md](./DEPLOYMENT.md) | Infra and env vars |
| [STRIPE_SETUP.md](./STRIPE_SETUP.md) | Payments |
| [BUG_REPORT.md](./BUG_REPORT.md) | Defect tracking |
