"""Vérifie la configuration de preprod/prod (config.settings.prod).

Ces settings ne sont jamais chargés par la suite de tests (qui tourne sur
config.settings.test) : sans ces tests, une erreur n'apparaîtrait qu'au déploiement.
"""

import importlib

import pytest


def _charger_prod(monkeypatch, **env):
    monkeypatch.setenv("ALLOWED_HOSTS", env.pop("ALLOWED_HOSTS", "ledgera.ubbfy.com"))
    monkeypatch.setenv("EMAIL_HOST", env.pop("EMAIL_HOST", "mail.exemple.com"))
    for cle, valeur in env.items():
        monkeypatch.setenv(cle, valeur)
    from config.settings import prod

    return importlib.reload(prod)


def test_debug_desactive(monkeypatch):
    assert _charger_prod(monkeypatch).DEBUG is False


def test_allowed_hosts_et_csrf_depuis_env(monkeypatch):
    prod = _charger_prod(monkeypatch, ALLOWED_HOSTS="ledgera.ubbfy.com")
    assert prod.DOMAINES_PUBLICS == ["ledgera.ubbfy.com"]
    # CSRF : seulement le domaine public, jamais les hôtes internes
    assert prod.CSRF_TRUSTED_ORIGINS == ["https://ledgera.ubbfy.com"]


def test_allowed_hosts_accepte_les_sondes_internes(monkeypatch):
    """Le HEALTHCHECK Docker interroge localhost : sans ces hôtes, Django renvoie 400
    et le conteneur reste unhealthy, bloquant le déploiement."""
    prod = _charger_prod(monkeypatch, ALLOWED_HOSTS="ledgera.ubbfy.com")
    assert "ledgera.ubbfy.com" in prod.ALLOWED_HOSTS
    assert "localhost" in prod.ALLOWED_HOSTS
    assert "127.0.0.1" in prod.ALLOWED_HOSTS


def test_cookies_securises_et_proxy_tls(monkeypatch):
    prod = _charger_prod(monkeypatch)
    assert prod.SESSION_COOKIE_SECURE is True
    assert prod.CSRF_COOKIE_SECURE is True
    assert prod.SESSION_COOKIE_HTTPONLY is True
    # Sans cet en-tête, Django derrière Traefik se croirait en HTTP -> boucle de redirection
    assert prod.SECURE_PROXY_SSL_HEADER == ("HTTP_X_FORWARDED_PROTO", "https")


def test_whitenoise_insere_une_seule_fois_et_ordre_middleware(monkeypatch):
    prod = _charger_prod(monkeypatch)
    m = prod.MIDDLEWARE
    # Un rechargement du module ne doit pas dupliquer l'entrée (pas de mutation en place)
    assert m.count("whitenoise.middleware.WhiteNoiseMiddleware") == 1
    assert m.index("whitenoise.middleware.WhiteNoiseMiddleware") == 1  # juste après SecurityMiddleware
    # Le middleware tenant doit rester APRÈS l'authentification (il lit request.user)
    assert m.index("apps.core.middleware.TenantSessionMiddleware") > m.index(
        "django.contrib.auth.middleware.AuthenticationMiddleware"
    )


def test_hsts_desactive_par_defaut(monkeypatch):
    # HSTS est irréversible côté navigateur : il ne doit pas s'activer tout seul en preprod
    assert _charger_prod(monkeypatch).SECURE_HSTS_SECONDS == 0


def test_smtp_465_bascule_en_ssl_et_desactive_tls(monkeypatch):
    # Django refuse EMAIL_USE_TLS et EMAIL_USE_SSL simultanément
    prod = _charger_prod(monkeypatch, EMAIL_PORT="465", EMAIL_USE_SSL="true", EMAIL_USE_TLS="true")
    assert prod.EMAIL_PORT == 465
    assert prod.EMAIL_USE_SSL is True
    assert prod.EMAIL_USE_TLS is False


def test_smtp_587_reste_en_starttls(monkeypatch):
    prod = _charger_prod(monkeypatch, EMAIL_PORT="587", EMAIL_USE_SSL="false", EMAIL_USE_TLS="true")
    assert prod.EMAIL_USE_TLS is True
    assert prod.EMAIL_USE_SSL is False


def test_smtp_obligatoire(monkeypatch):
    """Sans SMTP, personne ne peut valider son email : on refuse de démarrer."""
    monkeypatch.setenv("ALLOWED_HOSTS", "ledgera.ubbfy.com")
    monkeypatch.delenv("EMAIL_HOST", raising=False)
    from config.settings import prod

    with pytest.raises(KeyError):
        importlib.reload(prod)


def test_allowed_hosts_obligatoire(monkeypatch):
    """DEBUG=False sans ALLOWED_HOSTS = toutes les requêtes rejetées : on refuse de démarrer."""
    monkeypatch.delenv("ALLOWED_HOSTS", raising=False)
    monkeypatch.setenv("EMAIL_HOST", "mail.exemple.com")
    from config.settings import prod

    with pytest.raises(KeyError):
        importlib.reload(prod)
