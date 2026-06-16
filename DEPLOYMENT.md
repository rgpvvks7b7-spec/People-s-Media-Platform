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
FRONTEND_URL=https://yourdomain.com
STRIPE_SECRET_KEY=sk_live_or_test_key
STRIPE_WEBHOOK_SECRET=whsec_live_or_test_secret
STRIPE_CURRENCY=usd
```

Update Django settings before production launch:

- Read `SECRET_KEY`, `DEBUG`, and `ALLOWED_HOSTS` from env.
- Replace SQLite with PostgreSQL.
- Move uploaded media to object storage.
- Set production `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS`.
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
npm run build
```

Deploy `frontend/dist`.

Before production, move the API base URL out of `frontend/src/main.jsx` and into a Vite env var such as `VITE_API_URL`.

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
