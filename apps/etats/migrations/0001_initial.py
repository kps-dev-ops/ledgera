from django.db import migrations


class Migration(migrations.Migration):
    """L'app etats n'a pas de modèle Django. Cette migration sert de point
    d'ancrage pour les migrations RunSQL ultérieures (vue matérialisée)."""

    initial = True
    dependencies = [
        ("comptabilite", "0003_pg_triggers"),
    ]
    operations = []
