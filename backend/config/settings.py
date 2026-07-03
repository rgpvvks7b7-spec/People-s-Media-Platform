import os
from pathlib import Path
from urllib.parse import unquote, urlparse

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

BASE_DIR = Path(__file__).resolve().parent.parent
if load_dotenv:
    load_dotenv(BASE_DIR / '.env')


def env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}


def env_list(name, default=None):
    value = os.getenv(name)
    if value is None:
        return default or []
    return [item.strip() for item in value.split(',') if item.strip()]


def default_frontend_origins():
    origins = []
    for port in (5173, 5180, 4173):
        origins.extend([f'http://localhost:{port}', f'http://127.0.0.1:{port}'])
    frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:5173').rstrip('/')
    if frontend_url and frontend_url not in origins:
        origins.append(frontend_url)
    return origins

SECRET_KEY = os.getenv('SECRET_KEY', 'dev-only-change-this')
DEBUG = env_bool('DEBUG', True)
ALLOWED_HOSTS = env_list('ALLOWED_HOSTS', [])

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'accounts',
    'artists',
    'posts',
    'subscriptions',
    'mediahub',
    'marketplace',
    'discovery',
    'notifications',
    'livehub',
    'artistcalendar',
    'challenges',
    'spaces',
    'promotions',
    'campaigns',
    'moderation',
    'originlock',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'config.security_middleware.SecurityHeadersMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'
TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [],
    'APP_DIRS': True,
    'OPTIONS': {'context_processors': [
        'django.template.context_processors.request',
        'django.contrib.auth.context_processors.auth',
        'django.contrib.messages.context_processors.messages',
    ]},
}]
WSGI_APPLICATION = 'config.wsgi.application'

def configure_database():
    database_url = os.getenv('DATABASE_URL', '').strip()
    if not database_url:
        return {
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': BASE_DIR / 'db.sqlite3',
                # WAL mode lets readers and a writer work concurrently, and the
                # busy timeout makes contending writers wait instead of failing
                # with "database is locked" under SQLite in dev/test.
                'OPTIONS': {
                    'timeout': 20,
                    'transaction_mode': 'IMMEDIATE',
                    'init_command': (
                        'PRAGMA journal_mode=WAL;'
                        'PRAGMA synchronous=NORMAL;'
                        'PRAGMA busy_timeout=20000;'
                    ),
                },
            }
        }

    parsed = urlparse(database_url)
    engine = 'django.db.backends.postgresql'
    if parsed.scheme.startswith('postgres'):
        engine = 'django.db.backends.postgresql'
    elif parsed.scheme.startswith('mysql'):
        engine = 'django.db.backends.mysql'

    return {
        'default': {
            'ENGINE': engine,
            'NAME': unquote(parsed.path.lstrip('/')),
            'USER': unquote(parsed.username or ''),
            'PASSWORD': unquote(parsed.password or ''),
            'HOST': parsed.hostname or '',
            'PORT': str(parsed.port or ''),
        }
    }


DATABASES = configure_database()

AUTH_USER_MODEL = 'accounts.User'
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Australia/Melbourne'
USE_I18N = True
USE_TZ = True
STATIC_URL = 'static/'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
MEDIA_STREAM_TOKEN_SECONDS = int(os.getenv('MEDIA_STREAM_TOKEN_SECONDS', '3600'))
SERVE_LOCAL_MEDIA = env_bool('SERVE_LOCAL_MEDIA', True)
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:5173')

from config.platform_mode import normalize_platform_mode

PLATFORM_MODE = normalize_platform_mode(os.getenv('PLATFORM_MODE', 'live'))
DEFAULT_FRONTEND_ORIGINS = default_frontend_origins()
CORS_ALLOWED_ORIGINS = env_list('CORS_ALLOWED_ORIGINS', DEFAULT_FRONTEND_ORIGINS)
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = env_list('CSRF_TRUSTED_ORIGINS', DEFAULT_FRONTEND_ORIGINS)
SECURE_SSL_REDIRECT = env_bool('SECURE_SSL_REDIRECT', not DEBUG)
SESSION_COOKIE_SECURE = env_bool('SESSION_COOKIE_SECURE', not DEBUG)
CSRF_COOKIE_SECURE = env_bool('CSRF_COOKIE_SECURE', not DEBUG)
# Same-origin Vite /api proxy in dev; Lax is correct for first-party fetches.
SESSION_COOKIE_SAMESITE = os.getenv('SESSION_COOKIE_SAMESITE', 'Lax')
CSRF_COOKIE_SAMESITE = os.getenv('CSRF_COOKIE_SAMESITE', 'Lax')
SECURE_HSTS_SECONDS = int(os.getenv('SECURE_HSTS_SECONDS', '0' if DEBUG else '31536000'))
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool('SECURE_HSTS_INCLUDE_SUBDOMAINS', not DEBUG)
SECURE_HSTS_PRELOAD = env_bool('SECURE_HSTS_PRELOAD', False)
if env_bool('SECURE_PROXY_SSL_HEADER', not DEBUG):
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
REQUIRE_EMAIL_VERIFICATION = env_bool('REQUIRE_EMAIL_VERIFICATION', not DEBUG)
CONTENT_SECURITY_POLICY = os.getenv(
    'CONTENT_SECURITY_POLICY',
    "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data: blob: https:; media-src 'self' blob: https:; connect-src 'self' https:; "
    "frame-src https://www.youtube.com https://www.tiktok.com https://www.instagram.com; "
    "object-src 'none'; base-uri 'self'; form-action 'self'",
)
STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY', '')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET', '')
STRIPE_CURRENCY = os.getenv('STRIPE_CURRENCY', 'usd')
STRIPE_AUTOMATIC_TAX = env_bool('STRIPE_AUTOMATIC_TAX', not DEBUG)

# Used to fetch verified YouTube subscriber counts. When unset, reach is shown
# as "Pending verification" rather than any artist-supplied figure.
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY', '')

# SPA bootstraps many parallel API calls; keep throttling off in local DEBUG unless forced on.
API_THROTTLE_ENABLED = env_bool('API_THROTTLE_ENABLED', not DEBUG)

REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ] if API_THROTTLE_ENABLED else [],
    'DEFAULT_THROTTLE_RATES': {
        'anon': os.getenv('API_THROTTLE_ANON', '120/min'),
        'user': os.getenv('API_THROTTLE_USER', '600/min'),
        'auth': os.getenv('API_THROTTLE_AUTH', '20/min'),
        'checkout': os.getenv('API_THROTTLE_CHECKOUT', '30/min'),
        'promotion': os.getenv('API_THROTTLE_PROMOTION', '60/min'),
        'upload': os.getenv('API_THROTTLE_UPLOAD', '30/min'),
    },
}

WEBPUSH_VAPID_PUBLIC_KEY = os.getenv('WEBPUSH_VAPID_PUBLIC_KEY', '')
WEBPUSH_VAPID_PRIVATE_KEY = os.getenv('WEBPUSH_VAPID_PRIVATE_KEY', '')
WEBPUSH_VAPID_SUBJECT = os.getenv('WEBPUSH_VAPID_SUBJECT', 'mailto:noreply@indiefund.local')

EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = os.getenv('EMAIL_HOST', '')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = env_bool('EMAIL_USE_TLS', True)
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'IndieFund <noreply@indiefund.local>')

USE_S3_MEDIA = env_bool('USE_S3_MEDIA', False)
if USE_S3_MEDIA:
    INSTALLED_APPS.append('storages')
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID', '')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY', '')
    AWS_STORAGE_BUCKET_NAME = os.getenv('AWS_STORAGE_BUCKET_NAME', '')
    AWS_S3_REGION_NAME = os.getenv('AWS_S3_REGION_NAME', 'us-east-1')
    AWS_DEFAULT_ACL = None
    AWS_QUERYSTRING_AUTH = True
    AWS_S3_FILE_OVERWRITE = False
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    SERVE_LOCAL_MEDIA = False

from config.logging_config import configure_logging

LOGGING = configure_logging(DEBUG)
