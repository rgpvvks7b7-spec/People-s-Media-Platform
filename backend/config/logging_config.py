import logging
import os


def configure_logging(debug=False):
    level = "DEBUG" if debug else "INFO"
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "verbose": {
                "format": "{levelname} {asctime} {name} {message}",
                "style": "{",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "verbose",
            },
        },
        "root": {
            "handlers": ["console"],
            "level": level,
        },
        "loggers": {
            "django.request": {"level": "WARNING", "propagate": True},
            "stripe": {"level": "INFO", "propagate": True},
            "indiefund": {"level": level, "propagate": True},
        },
    }

    sentry_dsn = os.getenv("SENTRY_DSN", "").strip()
    if sentry_dsn:
        try:
            import sentry_sdk
            from sentry_sdk.integrations.django import DjangoIntegration

            sentry_sdk.init(
                dsn=sentry_dsn,
                integrations=[DjangoIntegration()],
                traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
                send_default_pii=False,
                environment=os.getenv("SENTRY_ENVIRONMENT", "production" if not debug else "development"),
            )
        except ImportError:
            logging.getLogger("indiefund").warning("SENTRY_DSN set but sentry-sdk is not installed")

    return config
