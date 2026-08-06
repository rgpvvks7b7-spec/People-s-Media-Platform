# Product Roadmap

**Platform:** IndieFund Indie Artist Platform  
**Maintained by:** Product  
**Last updated:** 2026-06-28  
**Beta status:** Phases 1–5 complete · Pre-launch hardening in progress · not production-ready  
**Launch plan:** [PRELAUNCH_STRATEGY.md](./PRELAUNCH_STRATEGY.md)

---

## North star

Help independent artists build sustainable income from real fans — not algorithm chasing — through subscriptions, local shows, merch, and fair discovery.

**Primary metrics**
- Artist: MRR + tips + marketplace revenue; supporter-to-follower ratio; local gig bookings
- Fan: artists supported (of 50 cap); discovery saves/follows; show attendance
- Platform: GMV, take rate (10% support — 5% on paid plans · 0% tips · 15% marketplace — 12% on Studio), Artist Pro / Studio conversion

---

## Current state

| Area | Shipped | Gap |
|------|---------|-----|
| Fan subscriptions & tips | Stripe Checkout, tiers, billing portal | E2E checkout coverage missing |
| Marketplace & commissions | Store cart, Connect payouts | Upload / fulfillment flows untested E2E |
| Local scene | Spaces, My Scene, tickets, check-in | Mobile nav broken (BUG-003) |
| Discovery | Swipe review, promoted releases (capped ads) | Gesture / signal E2E missing |
| Artist studio | Posts, music, calendar, live, promote | Studio flows untested E2E |
| Growth loops | Referrals, challenges, journey rollups | Challenge UI discoverability TBD |
| Trust & SEO | Public artist pages, meta, robots | Session hydration broken (BUG-001) |

---

## Prioritized backlog

### P0 — Release blockers (Sprint 0) — ✅ DONE (2026-06-23)

Fixed before any new beta invites or marketing push.

1. ~~**BUG-001** Session persistence on reload~~ — ✅ relative API proxy (`VITE_API_URL=/api`)
2. ~~**BUG-002** Registration success feedback~~ — ✅ shows on success; test now fills required fields
3. ~~**BUG-003** Mobile bottom navigation~~ — ✅ renders on mobile; helper made viewport-agnostic
4. ~~**E2E green**~~ — ✅ smoke (4) + beta (18) + qa-audit (42) + checkout (4) = 68 passing
5. ~~**Checkout E2E**~~ — ✅ subscription, tip, ticket, cart (`npm run test:e2e:checkout`)

### P1 — Onboarding & mobile quality (Sprint 1)

5. **BUG-004 / BUG-005** Registration labels + validation UX (WCAG 2.1)
6. ~~**First-session checklist**~~ — ✅ fan + artist + host dashboards ([PRELAUNCH_STRATEGY.md](./PRELAUNCH_STRATEGY.md) Phase 3.1)
7. **PWA polish** — manifest, safe-area, add-to-home-screen prompt (see [MOBILE_APP.md](./MOBILE_APP.md))
8. ~~**Checkout E2E**~~ — ✅ subscription, tip, ticket, cart (Stripe test mode)

### P1b — Pre-launch (see [PRELAUNCH_STRATEGY.md](./PRELAUNCH_STRATEGY.md))

| Order | Item |
|-------|------|
| 1 | Phase 0 — CI + staging + E2E hardening |
| 2 | Phase 1 — `PLATFORM_MODE` + fan gates |
| 3 | Phase 2 — Creator landing + fan waitlist |
| 4 | Phase 3 — Tier templates, host wizard, payout nudge |
| 5 | Phase 4 — Legal + transactional email |
| 6 | Phase 5 — Early signup open (creators only) |
| 7 | Phase 6 — Launch day flip |

### P2 — Growth (Sprint 2–3)

#### Artist growth
9. **Challenge board surfacing** — daily/weekly goals on artist dashboard (backend exists; make front-and-center)
10. **Invite funnel analytics** — track referral → follow → subscribe conversion in dashboard
11. **Local draw playbook** — guided flow: set city → book Spaces gig → promote to local fans
12. **Pro insights expansion** — “fans also support”, journey funnel, mailing list growth (partially built)

#### Fan engagement
13. **Discovery streaks** — reward consistent saves/listens (ties to fan discovery credits)
14. **My Scene notifications** — push when saved artist adds nearby show
15. **Post-show loop** — check-in → review → follow artist if guest
16. **Fan radio / playlists** — deepen My Music retention (partially built)

#### Monetization
17. **Support tier templates** — one-click tier setup for new artists ($1 / $5 / custom)
18. **Tip prompts at peak moments** — after full listen, post-show check-in, live end
19. **Discovery ad credits UX** — clearer Studio plan value ($25/mo credits, $100 cap campaigns)
20. **Commission inbox** — Pro feature visibility for custom work requests

### P3 — Scale & production (Sprint 4+)

21. **Production deploy** — PostgreSQL, S3, HTTPS cookies (see [DEPLOYMENT.md](./DEPLOYMENT.md))
22. **Cross-browser E2E** — WebKit + Firefox
23. **Performance budgets** — LCP on discover, stream latency
24. **Capacitor native shell** — iOS/Android wrapper after PWA stable
25. **50-subscription limit extension** — paid fan tier or one-time unlock (blueprint item)

---

## Feature themes (detailed recommendations)

### Artist growth

| Initiative | Why | Effort | Impact |
|------------|-----|--------|--------|
| Dashboard “next best action” | Challenges exist but artists need one obvious CTA | M | High |
| Referral leaderboard (local) | Reinforces scene-building vs global virality | M | Medium |
| Gig → discovery boost | Auto-suggest promoted campaign when calendar event goes live | S | High |
| Trust checklist completion | Unlocks discover ranking + host booking credibility | S | Medium |
| Mailing list export nudge | Drives Artist Pro conversion at 10+ email opt-ins | S | Medium |

### Fan engagement

| Initiative | Why | Effort | Impact |
|------------|-----|--------|--------|
| Session fix (BUG-001) | Saved artists / personalized discover require auth state | S | Critical |
| Swipe undo + skip reasons | Improves discovery signal quality | S | Medium |
| “Playing near you” on Home | Already on Discover cards; promote on fan Home | S | High |
| Push for drops & lives | Web push wired; need opt-in prompts + copy | M | High |
| Fan discovery credits redemption | Two-sided ad economy partially built; surface in tip/checkout UI | M | Medium |

### Monetization

| Initiative | Why | Effort | Impact |
|------------|-----|--------|--------|
| Stripe E2E + receipt emails | Revenue paths exist but untested end-to-end | M | Critical |
| Supporter-only stream previews | 10s/30s/60s tiers drive subscription conversion | S | High |
| Store bundle drops | Calendar + merch + music bundle checkout | L | Medium |
| Artist Pro / Studio checkout in-app | Plan definitions in `platform_fees.py`; complete upgrade funnel | M | High |
| Host revenue share | Spaces bookings + ticket fees (platform fee model TBD) | L | Medium |

---

## Test coverage roadmap

Aligns with [BUG_REPORT.md](./BUG_REPORT.md) gaps.

| Quarter | Add E2E for |
|---------|-------------|
| Sprint 0 | Auth persistence, registration, mobile nav |
| Sprint 1 | Subscription checkout, tips, ticket purchase |
| Sprint 2 | Music/artwork upload, artist post + calendar |
| Sprint 3 | Discovery swipe/save, live session smoke |
| Sprint 4 | Error states, throttling, cross-browser |

---

## Dependencies & docs

| Doc | Purpose |
|-----|---------|
| [PRELAUNCH_STRATEGY.md](./PRELAUNCH_STRATEGY.md) | Phased build order through launch day |
| [BUG_REPORT.md](./BUG_REPORT.md) | Open defects + repro steps |
| [FIX_LOG.md](./FIX_LOG.md) | Resolved fixes + verification |
| [BETA_PHASES.md](./BETA_PHASES.md) | Completed beta scope |
| [PROJECT_BLUEPRINT.md](./PROJECT_BLUEPRINT.md) | Original product rules |
| [STRIPE_SETUP.md](./STRIPE_SETUP.md) | Payments configuration |
| [DEPLOYMENT.md](./DEPLOYMENT.md) | Production checklist |

---

## Decision log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-06-28 | Pre-launch strategy: no artist beta QA; early creator signup then fan launch | [PRELAUNCH_STRATEGY.md](./PRELAUNCH_STRATEGY.md) |
| 2026-06-23 | Gate beta expansion on P0 bug fixes | QA shows auth + mobile broken despite Phase 5 “complete” |
| 2026-06-23 | Prioritize checkout E2E before new monetization features | Revenue paths shipped but unverified |
| 2026-06-23 | Surface existing challenges/journey before new growth features | Backend metrics exist; UI leverage is cheaper than new systems |
