"""Settings de production / preprod.

Activé par `DJANGO_SETTINGS_MODULE=config.settings.prod` (défaut de wsgi/asgi).

Contexte de déploiement :
- **domaine unique** (ex. ledgera.ubbfy.com) : le tenant est choisi par l'utilisateur
  connecté (`TenantSessionMiddleware`), pas par le nom d'hôte ;
- TLS terminé en amont par Traefik/Coolify → l'app reçoit du HTTP + `X-Forwarded-Proto` ;
- fichiers statiques servis par WhiteNoise (pas de serveur web dédié).

Les variables d'environnement sans valeur par défaut sont **obligatoires** : l'app refuse
de démarrer si elles manquent, plutôt que de tourner dans une configuration douteuse.
"""

import os

from .base import *  # noqa: F403

DEBUG = False

# --- Domaine ---------------------------------------------------------------
# Obligatoire : sans lui, Django refuserait toutes les requêtes (DEBUG=False).
ALLOWED_HOSTS = [h.strip() for h in os.environ["ALLOWED_HOSTS"].split(",") if h.strip()]
CSRF_TRUSTED_ORIGINS = [f"https://{h}" for h in ALLOWED_HOSTS]

# --- Sécurité derrière le reverse proxy ------------------------------------
# Traefik/Coolify terminent le TLS et transmettent l'en-tête ci-dessous ; sans elle,
# Django croirait être en HTTP et boucler sur les redirections HTTPS.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = os.environ.get("SECURE_SSL_REDIRECT", "True").lower() == "true"

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"

# HSTS : désactivé par défaut, volontairement.
# Une fois l'en-tête envoyé, les navigateurs REFUSENT le HTTP sur ce domaine pendant
# toute la durée annoncée — irréversible côté client. À n'activer qu'une fois le HTTPS
# stabilisé en production (ex. SECURE_HSTS_SECONDS=31536000).
SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", "0"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = os.environ.get("SECURE_HSTS_INCLUDE_SUBDOMAINS", "False").lower() == "true"
SECURE_HSTS_PRELOAD = False

# --- Fichiers statiques (WhiteNoise) ---------------------------------------
# Nouvelle liste (pas d'insertion en place) : muter MIDDLEWARE de base dupliquerait
# l'entrée si ce module était rechargé.
MIDDLEWARE = [
    MIDDLEWARE[0],  # noqa: F405  (SecurityMiddleware)
    "whitenoise.middleware.WhiteNoiseMiddleware",
    *MIDDLEWARE[1:],  # noqa: F405
]

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

# --- Email -----------------------------------------------------------------
# Obligatoire : allauth exige la vérification de l'adresse (ACCOUNT_EMAIL_VERIFICATION
# = "mandatory"). Sans SMTP fonctionnel, personne ne peut finaliser sa connexion.
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.environ["EMAIL_HOST"]
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
# Port 465 = SSL implicite (USE_SSL) ; port 587 = STARTTLS (USE_TLS).
# Django interdit les deux à True simultanément.
EMAIL_USE_SSL = os.environ.get("EMAIL_USE_SSL", "False").lower() == "true"
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "True").lower() == "true" and not EMAIL_USE_SSL
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", EMAIL_HOST_USER or "no-reply@localhost")
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# --- Logs ------------------------------------------------------------------
# Vers stdout : agrégés par Coolify/Docker.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"simple": {"format": "{levelname} {asctime} {name} {message}", "style": "{"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "simple"}},
    "root": {"handlers": ["console"], "level": os.environ.get("LOG_LEVEL", "INFO")},
    "loggers": {
        "django.request": {"handlers": ["console"], "level": "ERROR", "propagate": False},
    },
}
