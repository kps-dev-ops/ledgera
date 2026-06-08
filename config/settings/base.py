import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = os.environ["SECRET_KEY"]

ALLOWED_HOSTS = [h.strip() for h in os.environ.get("ALLOWED_HOSTS", "localhost").split(",")]

# django-tenants : SHARED_APPS d'abord, TENANT_APPS ensuite
SHARED_APPS = [
    "django_tenants",
    "apps.core",
    "apps.tenants",
    "apps.referentiels",
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "django.contrib.admin",
    "allauth",
    "allauth.account",
    "allauth.mfa",
    "axes",
    "django_celery_beat",
    "unfold",
    "tailwind",
    "theme",
    "django_browser_reload",
    "crispy_forms",
    "crispy_tailwind",
    "django_htmx",
    "django_otp",
    "django_otp.plugins.otp_totp",
    "django_otp.plugins.otp_static",
]

TENANT_APPS = [
    "apps.audit",  # Piste d'audit par société (triggers PG, lecture seule)
    "apps.comptabilite",  # M1 : journaux, écritures, pièces, périodes
    "apps.tiers",  # M2 : clients, fournisseurs, lettrage
    "apps.immobilisations",  # M3 : immos, amortissements, cessions
    "apps.etats",  # M5 : balance, grand livre, journal, bilan, CR
    "apps.imports_exports",  # M7 : imports Excel, exports FEC/Excel/PDF
    # apps.banque — ajouté en L3b
]

INSTALLED_APPS = list(SHARED_APPS) + [app for app in TENANT_APPS if app not in SHARED_APPS]

TENANT_MODEL = "tenants.Societe"
TENANT_DOMAIN_MODEL = "tenants.Domain"

MIDDLEWARE = [
    "django_tenants.middleware.main.TenantMainMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django_otp.middleware.OTPMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "axes.middleware.AxesMiddleware",
    "apps.core.middleware.AuditContextMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django_tenants.postgresql_backend",
        "NAME": os.environ.get("DB_NAME", "ledgera"),
        "USER": os.environ.get("DB_USER", "ledgera"),
        "PASSWORD": os.environ.get("DB_PASSWORD", "ledgera"),
        "HOST": os.environ.get("DB_HOST", "localhost"),
        "PORT": os.environ.get("DB_PORT", "5432"),
    }
}

DATABASE_ROUTERS = ["django_tenants.routers.TenantSyncRouter"]

AUTH_USER_MODEL = "core.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
]

LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "Africa/Porto-Novo"
USE_I18N = True
USE_TZ = True
# Formatage français : séparateur de milliers (espace) + virgule décimale
USE_THOUSAND_SEPARATOR = True
NUMBER_GROUPING = 3
DECIMAL_SEPARATOR = ","
THOUSAND_SEPARATOR = " "  # espace fine insécable (NARROW NO-BREAK SPACE)

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Allauth
AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]
# allauth v65+ API
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/accounts/login/"

# Axes (brute-force protection)
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 0.25  # 15 minutes

# Crispy forms (Tailwind)
CRISPY_ALLOWED_TEMPLATE_PACKS = "tailwind"
CRISPY_TEMPLATE_PACK = "tailwind"

# django-tailwind
TAILWIND_APP_NAME = "theme"
INTERNAL_IPS = ["127.0.0.1"]

# Celery
CELERY_BROKER_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_RESULT_EXPIRES = 60 * 60 * 24  # 24 heures
CELERY_TIMEZONE = TIME_ZONE

# Session
SESSION_COOKIE_AGE = 4 * 60 * 60  # 4 heures
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
