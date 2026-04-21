#!/bin/bash
set -e

echo "Attente PostgreSQL..."
until python -c "import psycopg; psycopg.connect('$DATABASE_URL')" 2>/dev/null; do
  sleep 1
done

echo "Migrations shared..."
python manage.py migrate_schemas --shared --noinput

echo "Démarrage Gunicorn..."
exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 2 --timeout 120
