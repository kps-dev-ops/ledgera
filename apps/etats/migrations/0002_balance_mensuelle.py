from django.db import migrations

CREATE_MATVIEW = """
CREATE MATERIALIZED VIEW IF NOT EXISTS balance_mensuelle AS
SELECT
    pc.exercice_id,
    EXTRACT(MONTH FROM pc.date_piece)::int AS mois,
    le.compte_id,
    SUM(le.debit) AS total_debit,
    SUM(le.credit) AS total_credit,
    SUM(le.debit - le.credit) AS solde
FROM comptabilite_ligneecriture le
JOIN comptabilite_piececomptable pc ON pc.id = le.piece_id
WHERE pc.statut = 'VALIDEE'
GROUP BY pc.exercice_id, EXTRACT(MONTH FROM pc.date_piece)::int, le.compte_id;

CREATE UNIQUE INDEX IF NOT EXISTS balance_mensuelle_uk
    ON balance_mensuelle (exercice_id, mois, compte_id);
"""

DROP_MATVIEW = """
DROP MATERIALIZED VIEW IF EXISTS balance_mensuelle CASCADE;
"""


class Migration(migrations.Migration):
    dependencies = [("etats", "0001_initial")]
    operations = [
        migrations.RunSQL(CREATE_MATVIEW, reverse_sql=DROP_MATVIEW),
    ]
