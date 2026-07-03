# Deployment Checklist

## Recommended split

- Backend: Render, Fly.io, Railway, AWS, or similar Python host
- Frontend: Vercel, Netlify, or static hosting from `frontend/dist`
- Database: PostgreSQL
- Media: S3-compatible object storage

## Backend environment

Set production environment variables:

```bash
SECRET_KEY=replace-me
DEBUG=False
ALLOWED_HOSTS=api.yourdomain.com
CORS_ALLOWED_ORIGINS=https://yourdomain.com
CSRF_TRUSTED_ORIGINS=https://yourdomain.com
FRONTEND_URL=https://yourdomain.com
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
SECURE_HSTS_PRELOAD=False
STRIPE_SECRET_KEY=sk_live_or_test_key
STRIPE_WEBHOOK_SECRET=whsec_live_or_test_secret
STRIPE_CURRENCY=usd
STRIPE_AUTOMATIC_TAX=True
REQUIRE_EMAIL_VERIFICATION=True
SECURE_PROXY_SSL_HEADER=True
DATABASE_URL=postgres://user:pass@host:5432/indiefund
USE_S3_MEDIA=True
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_STORAGE_BUCKET_NAME=
AWS_S3_REGION_NAME=us-east-1
SENTRY_DSN=
SENTRY_ENVIRONMENT=production
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
DEFAULT_FROM_EMAIL=IndieFund <noreply@yourdomain.com>
SUPPORT_EMAIL=support@yourdomain.com
# prelaunch = creators only (no fan signup/discovery); live = full platform
PLATFORM_MODE=live
```

Update Django settings before production launch:

- Replace SQLite with PostgreSQL.
- Move uploaded media to object storage.
- Serve static files through the host or a package like WhiteNoise.

## Deploy backend

```bash
cd backend
pip install -r requirements.txt
python3 manage.py migrate
python3 manage.py collectstatic
```

Use a production server such as Gunicorn:

```bash
gunicorn config.wsgi:application
```

## Deploy frontend

```bash
cd frontend
npm install
VITE_API_URL=https://api.yourdomain.com/api npm run build
```

Deploy `frontend/dist`.

The frontend reads its API base URL from `VITE_API_URL`. For local development, copy `frontend/.env.example` to `frontend/.env.local`.

### Transactional email (staging)

Configure SMTP in the backend env block above, then verify delivery:

```bash
cd backend
python manage.py test_transactional_email --to=you@example.com
```

This sends sample verification, waitlist confirmation, and ticket receipt messages.

### Legal & consent (before real email collection)

- Set Iubenda env vars in `frontend/.env.local` (see [legal/IUBENDA_SETUP.md](./legal/IUBENDA_SETUP.md))
- Keep `VITE_LEGAL_PRE_RELEASE=true` until lawyer sign-off; set to `false` at launch
- Complete [legal/CONSENT_CHECKLIST.md](./legal/CONSENT_CHECKLIST.md)

## Stripe production

- Add the production webhook endpoint in Stripe Dashboard:
  `https://api.yourdomain.com/api/subscriptions/stripe-webhook/`
- Listen for:
  - `checkout.session.completed`
  - `customer.subscription.updated`
  - `customer.subscription.deleted`
- Confirm supporter-only content unlocks only after webhook activation.

## Media security

Current local media is served directly by Django. For production:

- Store media in private object storage.
- Generate signed URLs for supporter-only audio/downloads.
- Keep cover images public if desired.
- Validate file extension, size, and content type.

## Backups

- **PostgreSQL:** Enable daily automated snapshots on your host (Render, Railway, Supabase, etc.). Retain at least 7 days.
- **Media (S3):** Enable bucket versioning. Lifecycle rules can move old versions to infrequent access after 30 days.
- **Restore drill:** Before launch, restore a snapshot to a staging database and verify login + media access.

```bash
# Example manual Postgres dump (run from a secure ops machine)
pg_dump "$DATABASE_URL" -Fc -f indiefund-$(date +%F).dump
```

## Monitoring

- Wire `/api/health/` to an uptime monitor (Better Uptime, Pingdom, etc.).
- Set `SENTRY_DSN` for error tracking. Logs use structured JSON via `LOGGING` in `config/settings.py`.
- Run `python manage.py beta_security_check` after every production deploy.

## Staging environment

Deploy a staging stack with `DEBUG=False`, Stripe **test** keys, and a separate `DATABASE_URL`. Set `PLATFORM_MODE=prelaunch` on staging to verify creator-only gates before fan launch; flip to `live` when ready. Run Playwright against staging before promoting to production:

```bash
cd frontend && npm run test:e2e
cd backend && python manage.py test && python manage.py beta_security_check
```
