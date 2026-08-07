# Launch artist program

Use this checklist to prepare a lively public launch. Code support: `python manage.py seed_launch_content` (marks recent artists featured) or pass a CSV of usernames.

## Target (15–25 artists)

Each launch artist should have before go-live:

- Complete profile (stage name, city, genre, story)
- 2+ tracks or portfolio posts
- 1+ store item or supporter tier
- Stripe Connect onboarding started (production)
- 1+ post scheduled for launch week

## Cities

Aim for 3–5 active cities (e.g. Melbourne, Sydney, Brisbane) so Discover and My Scene feel local.

## Soft open (1–2 weeks)

1. Invite launch artists + their mailing lists via personal invite links (`?ref=` attribution).
2. Run `python manage.py seed_launch_content artists.csv` to flag featured profiles.
3. Fix blockers from `python manage.py beta_security_check` on staging.
4. Run full E2E: `npm run test:e2e` in `frontend/`.

## Artist onboarding call (30 min)

- Walk through upload → post → Connect → share link
- Set first support tier ($1 / $5 / custom)
- Explain fee schedule (10% support — 5% on paid plans, 0% tips, 15% marketplace — 12% on Studio)

## Public launch

- Guest home shows featured artists
- FAQ and support@indiefund.app visible
- Marketing points to `/?page=discover` (in-app entry)
