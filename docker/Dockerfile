# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# Étape 1 — Compilation du CSS Tailwind
# Node n'est nécessaire QUE pour produire styles.css ; l'image finale ne l'embarque pas.
# ---------------------------------------------------------------------------
FROM node:20-slim AS tailwind

WORKDIR /build
COPY theme/static_src/package.json theme/static_src/package-lock.json* ./theme/static_src/
RUN cd theme/static_src && npm install
COPY theme ./theme
# Tailwind scanne les templates pour ne conserver que les classes réellement utilisées :
# d'où la copie de templates/ et apps/ ci-dessous.
COPY templates ./templates
COPY apps ./apps
RUN cd theme/static_src && npm run build

# ---------------------------------------------------------------------------
# Étape 2 — Image applicative
# ---------------------------------------------------------------------------
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=config.settings.prod

WORKDIR /app

# libpq : PostgreSQL. Les suivantes : dépendances système de WeasyPrint (édition PDF
# des bordereaux et états) — sans elles, l'import de weasyprint échoue à l'exécution.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    libpango-1.0-0 libpangoft2-1.0-0 libcairo2 libgdk-pixbuf-2.0-0 \
    libffi-dev shared-mime-info fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
# Dépendances de production uniquement : plus de [dev] (pytest, ruff, mypy n'ont
# rien à faire dans une image déployée).
RUN pip install --no-cache-dir uv && uv pip install --system -e "."

COPY . .

# CSS compilé récupéré depuis l'étape Node : le dossier dist/ est gitignoré, il
# n'existe donc pas dans le contexte de build.
COPY --from=tailwind /build/theme/static/css/dist ./theme/static/css/dist

COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["/entrypoint.sh"]
