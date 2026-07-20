# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# Étape 1 — Compilation du CSS Tailwind
# Node n'est nécessaire QUE pour produire styles.css ; l'image finale ne l'embarque pas.
# Le dossier theme/static/css/dist est gitignoré : il n'existe pas dans le contexte
# de build, il faut donc le fabriquer ici.
# ---------------------------------------------------------------------------
FROM node:20-slim AS tailwind

WORKDIR /build

# package-lock.json d'abord : cette couche n'est reconstruite que si les
# dépendances changent, pas à chaque modification de template.
COPY theme/static_src/package.json theme/static_src/package-lock.json ./theme/static_src/
RUN cd theme/static_src && npm ci

# Tailwind purge les classes inutilisées en scannant les sources : les templates
# et le code applicatif doivent être présents, sinon le CSS produit serait vide.
COPY theme ./theme
COPY templates ./templates
COPY apps ./apps
RUN cd theme/static_src && npm run build

# ---------------------------------------------------------------------------
# Étape 2 — Image applicative
# ---------------------------------------------------------------------------
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings.prod

WORKDIR /app

# libpq/gcc : compilation éventuelle des dépendances Python.
# libpango, libcairo, libgdk-pixbuf, shared-mime-info : dépendances SYSTÈME de
# WeasyPrint. Sans elles, l'import de weasyprint échoue et toutes les éditions PDF
# (bordereaux fiscaux, états) tombent en erreur à l'exécution.
# fonts-dejavu-core : sans police, les PDF sortent sans texte.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    libpango-1.0-0 libpangoft2-1.0-0 libcairo2 libgdk-pixbuf-2.0-0 \
    libffi-dev shared-mime-info fonts-dejavu-core curl \
    && rm -rf /var/lib/apt/lists/*

# Dépendances Python avant le code : la couche est mise en cache tant que
# pyproject.toml ne bouge pas. Pas de [dev] : pytest/ruff/mypy n'ont rien à faire
# dans une image déployée.
# Ne référencer QUE des fichiers réellement versionnés : un motif qui ne
# correspond à rien (ex. README.md*) fait échouer BuildKit sur un clone frais.
COPY pyproject.toml ./
# hatchling déclare packages = ["apps", "config"] : ces deux dossiers doivent
# exister avant l'installation éditable.
COPY apps ./apps
COPY config ./config
RUN pip install --no-cache-dir uv && uv pip install --system -e "."

COPY . .

# CSS compilé récupéré de l'étape Node.
COPY --from=tailwind /build/theme/static/css/dist ./theme/static/css/dist

COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# collectstatic au BUILD, pas au demarrage : les fichiers statiques ne dependent
# pas de la configuration runtime. WhiteNoise (CompressedManifestStaticFilesStorage)
# compresse chaque fichier en gzip ET brotli — inutile de le refaire a chaque
# demarrage du conteneur. Bonus : une erreur de statiques casse le build au lieu
# de casser la production.
# Les valeurs ci-dessous ne servent qu'a charger les settings ; elles ne sont ni
# conservees dans l'image ni utilisees a l'execution (l'environnement reel prime).
RUN SECRET_KEY=build-only-jamais-utilise-a-l-execution \
    ALLOWED_HOSTS=localhost \
    EMAIL_HOST=localhost \
    python manage.py collectstatic --noinput --clear

# Utilisateur non privilégié : une faille applicative ne donne pas root dans le
# conteneur. /app doit rester inscriptible : collectstatic écrit dans staticfiles/
# au démarrage, et media/ reçoit les fichiers importés.
RUN useradd --create-home --uid 1000 ledgera \
    && mkdir -p /app/staticfiles /app/media \
    && chown -R ledgera:ledgera /app
USER ledgera

EXPOSE 8000

# Coolify/Traefik s'en servent pour savoir si le conteneur est réellement prêt.
# On interroge la page de login : joignable sans authentification ni société active.
# 127.0.0.1 est accepté par ALLOWED_HOSTS (cf. config/settings/prod.py), sinon Django
# répondrait 400 et le conteneur resterait unhealthy.
# start-period genereux : l'entrypoint attend la base, applique les migrations
# (shared + tenants) et lance collectstatic avant que Gunicorn n'ecoute.
HEALTHCHECK --interval=30s --timeout=5s --start-period=120s --retries=3 \
    CMD curl -fsS -o /dev/null http://127.0.0.1:8000/accounts/login/ || exit 1

ENTRYPOINT ["/entrypoint.sh"]
