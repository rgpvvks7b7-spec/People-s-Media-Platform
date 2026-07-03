# IndieFund Beta Fix Phases

## Phase 1 — Loop polish (complete)
Fixes fans/artists/hosts can feel without Stripe or production deploy.

- [x] Notification click → deep link (My Scene, Discover, artist pages)
- [x] Duplicate event ticket purchase blocked
- [x] My tickets in Profile
- [x] Host booking inbox shows artist local draw
- [x] Min local supporters help copy (host form + artist growth tips)
- [x] New fan getting-started path on Home
- [x] Purchase receipt message for tickets

**Verify:** `python manage.py test` + `python manage.py beta_scene_loop`

## Phase 2 — Commerce & notifications (complete)
- [x] Stripe Checkout for subscriptions (test mode)
- [x] Stripe Checkout for tickets / marketplace
- [x] Notification types wired for purchases
- [x] Saved artists page shows local gigs
- [x] Playing near you venue context on Discover cards
- [x] Profile completion checklist lists missing trust fields

**Verify:** `python manage.py test` + `python manage.py beta_scene_loop`

## Phase 3 — Host & show night (complete)
- [x] Host dashboard (requests + draw + confirm in one view)
- [x] Fan QR / “I'm here” check-in
- [x] Post-show review prompts for fans
- [x] Ticket email receipt (transactional)
- [x] Event ticket inventory per show
- [x] Store cart (add to cart + cart checkout)

**Verify:** `python manage.py test` + `python manage.py beta_scene_loop`

## Phase 4 — Money & production (complete)
- [x] Stripe Connect artist payout onboarding (Express + demo fallback)
- [x] PostgreSQL via `DATABASE_URL` (SQLite default for dev)
- [x] S3 media storage optional via `USE_S3_MEDIA`
- [x] Signed stream URLs for supporter-only audio
- [x] Billing portal (`POST /api/subscriptions/billing-portal/`)
- [x] Failed payment recovery (`invoice.payment_failed` + past_due notifications)

**Verify:** `python manage.py test` + `python manage.py beta_scene_loop`

## Phase 5 — Growth & polish (complete)
- [x] Public SEO artist pages (guest `?artist=` + meta tags + sitemap/robots)
- [x] Web push notifications (VAPID subscribe + service worker)
- [x] Mobile nav polish (5-item compact bottom nav for artists/fans)
- [x] Referral / invite links (invite link + follow-on-save attribution)
- [x] E2E Playwright suite (`frontend/npm run test:e2e`)
- [x] Load / security audit (`python manage.py beta_security_check` + API throttling)

**Verify:** `python manage.py test` + `python manage.py beta_scene_loop` + `npm run test:e2e`

Run autonomous checks after each phase:
```bash
cd backend && .venv/bin/python manage.py test
cd backend && .venv/bin/python manage.py beta_scene_loop
cd frontend && npm run test:beta
```
