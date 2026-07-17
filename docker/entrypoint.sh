#!/bin/bash
set -e

echo "Attente PostgreSQL..."
until python -c "import psycopg; psycopg.connect('$DATABASE_URL')" 2>/dev/null; do
  sleep 1
done

echo "Migrations du schema public (shared)..."
python manage.py migrate_schemas --shared --noinput

echo "Migrations des schemas tenants..."
# No-op tant qu'aucune societe n'existe. Indispensable des qu'il y en a une :
# sans cela, les schemas des societes restent en retard sur le code apres
# l'ajout d'une TENANT_APP ou d'une migration metier.
python manage.py migrate_schemas --tenant --noinput

echo "Collecte des fichiers statiques..."
# A l'execution et non au build : le storage manifeste de WhiteNoise a besoin des
# settings, donc des variables d'environnement.
python manage.py collectstatic --noinput --clear

echo "Demarrage Gunicorn..."
exec gunicorn config.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers "${GUNICORN_WORKERS:-3}" \
  --timeout 120 \
  --access-logfile - \
  --error-logfile -
