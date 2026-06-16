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
