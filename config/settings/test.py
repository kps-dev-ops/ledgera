import os

from .base import *  # noqa: F401, F403

DEBUG = False
SECRET_KEY = "test-insecure-key"

DATABASES = {
    "default": {
        "ENGINE": "django_tenants.postgresql_backend",
        "NAME": os.environ.get("DB_NAME", "ledgera"),
        "USER": os.environ.get("DB_USER", "ledgera"),
        "PASSWORD": os.environ.get("DB_PASSWORD", "ledgera"),
        "HOST": os.environ.get("DB_HOST", "localhost"),
        "PORT": os.environ.get("DB_PORT", "5432"),
        "TEST": {"NAME": os.environ.get("DB_TEST_NAME", "ledgera_test")},
    }
}

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
ACCOUNT_EMAIL_VERIFICATION = "none"
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
