# Stripe Local Setup

This app uses Stripe Checkout for monthly artist support.

## Install backend dependency

```bash
cd backend
pip install -r requirements.txt
```

## Configure test keys

Create `backend/.env`:

```bash
SECRET_KEY=dev-only-change-this
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
CSRF_TRUSTED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
FRONTEND_URL=http://localhost:5173
SECURE_SSL_REDIRECT=False
SESSION_COOKIE_SECURE=False
CSRF_COOKIE_SECURE=False
SECURE_HSTS_SECONDS=0
SECURE_HSTS_INCLUDE_SUBDOMAINS=False
SECURE_HSTS_PRELOAD=False
STRIPE_SECRET_KEY=sk_test_your_key
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret
STRIPE_CURRENCY=usd
```

## Run local servers

```bash
cd backend
python3 manage.py runserver localhost:8000
```

```bash
cd frontend
npm run dev -- --host localhost
```

## Forward Stripe webhooks locally

Install and log in to the Stripe CLI, then run:

```bash
stripe listen --forward-to localhost:8000/api/subscriptions/stripe-webhook/
```

Copy the printed `whsec_...` value into `backend/.env` as `STRIPE_WEBHOOK_SECRET`, then restart Django.

## Test payments

Use Stripe test cards in Checkout. For a normal successful card payment, use:

```text
4242 4242 4242 4242
```

Apple Pay appears in Stripe Checkout when Apple Pay is enabled in Stripe and the customer is using a supported Apple Pay device/browser.
