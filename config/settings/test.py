from .base import *  # noqa: F401, F403

DEBUG = False
SECRET_KEY = "test-insecure-key"

DATABASES = {
    "default": {
        "ENGINE": "django_tenants.postgresql_backend",
        "NAME": "ledgera_test",
        "USER": "ledgera",
        "PASSWORD": "ledgera",
        "HOST": "localhost",
        "PORT": "5432",
        "TEST": {"NAME": "ledgera_test"},
    }
}

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
ACCOUNT_EMAIL_VERIFICATION = "none"
CELERY_TASK_ALWAYS_EAGER = True
