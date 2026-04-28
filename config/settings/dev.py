
from .base import *  # noqa: F401, F403

DEBUG = True
SECRET_KEY = "dev-insecure-key-not-for-prod"

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django.db.backends": {"handlers": ["console"], "level": "DEBUG", "propagate": False},
    },
}

MIDDLEWARE = MIDDLEWARE + ["django_browser_reload.middleware.BrowserReloadMiddleware"]  # noqa: F405

AXES_ENABLED = False

NPM_BIN_PATH = r"C:\Program Files\nodejs\npm.cmd"
