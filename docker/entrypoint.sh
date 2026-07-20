#!/bin/bash
set -e

# ---------------------------------------------------------------------------
# Attente de PostgreSQL — avec diagnostic et timeout.
#
# Une boucle infinie silencieuse est un piege : le conteneur reste "starting"
# indefiniment et l'orchestrateur ne dit jamais POURQUOI. On affiche donc la
# vraie erreur de connexion et on abandonne apres DB_WAIT_TIMEOUT secondes.
# ---------------------------------------------------------------------------
: "${DB_WAIT_TIMEOUT:=60}"

if [ -z "$DATABASE_URL" ]; then
  echo "ERREUR : DATABASE_URL n'est pas definie." >&2
  exit 1
fi

# Cible affichee sans le mot de passe (diagnostic sans fuite de secret).
CIBLE=$(python - <<'PY'
import os
from urllib.parse import urlsplit
u = urlsplit(os.environ["DATABASE_URL"])
print(f"{u.hostname}:{u.port or 5432}/{(u.path or '/').lstrip('/')} (user={u.username})")
PY
)
echo "Attente PostgreSQL sur ${CIBLE} — timeout ${DB_WAIT_TIMEOUT}s..."

DERNIERE_ERREUR=""
for i in $(seq 1 "$DB_WAIT_TIMEOUT"); do
  if DERNIERE_ERREUR=$(python -c "
import os, sys, psycopg
try:
    psycopg.connect(os.environ['DATABASE_URL'], connect_timeout=3).close()
except Exception as e:
    # Message seul, sans traceback : c'est la cause qui compte, pas la pile.
    print(f'{type(e).__name__}: {e}'.strip(), file=sys.stderr)
    sys.exit(1)
" 2>&1); then
    echo "PostgreSQL joignable apres ${i}s."
    break
  fi
  # Trace la cause toutes les 10 tentatives : on voit tout de suite s'il s'agit
  # d'un nom d'hote non resolu, d'une base absente ou d'une auth refusee.
  if [ $((i % 10)) -eq 0 ]; then
    echo "  ... tentative ${i}/${DB_WAIT_TIMEOUT} : ${DERNIERE_ERREUR}" >&2
  fi
  if [ "$i" -eq "$DB_WAIT_TIMEOUT" ]; then
    echo "ERREUR : PostgreSQL injoignable apres ${DB_WAIT_TIMEOUT}s." >&2
    echo "Cible  : ${CIBLE}" >&2
    echo "Cause  : ${DERNIERE_ERREUR}" >&2
    echo "Pistes : le conteneur applicatif est-il sur le meme reseau Docker que" >&2
    echo "         la base ? la base existe-t-elle ? l'utilisateur/mot de passe" >&2
    echo "         correspondent-ils ? DATABASE_URL et les DB_* sont-ils coherents ?" >&2
    exit 1
  fi
  sleep 1
done

echo "Migrations du schema public (shared)..."
python manage.py migrate_schemas --shared --noinput

echo "Migrations des schemas tenants..."
# No-op tant qu'aucune societe n'existe. Indispensable des qu'il y en a une :
# sans cela, les schemas des societes restent en retard sur le code apres
# l'ajout d'une TENANT_APP ou d'une migration metier.
python manage.py migrate_schemas --tenant --noinput

# Les fichiers statiques sont deja collectes et compresses au BUILD (cf. Dockerfile) :
# rien a faire ici, le conteneur demarre d'autant plus vite.

echo "Demarrage Gunicorn..."
exec gunicorn config.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers "${GUNICORN_WORKERS:-3}" \
  --timeout 120 \
  --access-logfile - \
  --error-logfile -
