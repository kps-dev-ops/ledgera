from django.db import migrations

R9_EXERCICE_CLOTURE = """
CREATE OR REPLACE FUNCTION check_exercice_cloture() RETURNS trigger AS $body$
DECLARE
    ex_statut text;
    ex_id integer;
BEGIN
    IF TG_OP = 'DELETE' THEN
        ex_id := OLD.exercice_id;
    ELSE
        ex_id := NEW.exercice_id;
    END IF;
    SELECT statut INTO ex_statut FROM comptabilite_exercice WHERE id = ex_id;
    IF ex_statut = 'CLOTURE' THEN
        RAISE EXCEPTION 'R9 : exercice cloture, ecriture interdite (exercice_id=%)', ex_id;
    END IF;
    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END;
$body$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_exercice_cloture ON comptabilite_piececomptable;
CREATE TRIGGER trg_exercice_cloture
    BEFORE INSERT OR UPDATE OR DELETE ON comptabilite_piececomptable
    FOR EACH ROW EXECUTE FUNCTION check_exercice_cloture();

CREATE OR REPLACE FUNCTION check_ligne_exercice_cloture() RETURNS trigger AS $body$
DECLARE
    ex_statut text;
    p_id integer;
BEGIN
    IF TG_OP = 'DELETE' THEN
        p_id := OLD.piece_id;
    ELSE
        p_id := NEW.piece_id;
    END IF;
    SELECT e.statut INTO ex_statut
        FROM comptabilite_piececomptable p
        JOIN comptabilite_exercice e ON e.id = p.exercice_id
        WHERE p.id = p_id;
    IF ex_statut = 'CLOTURE' THEN
        RAISE EXCEPTION 'R9 : exercice cloture, ligne interdite (piece_id=%)', p_id;
    END IF;
    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END;
$body$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_ligne_exercice_cloture ON comptabilite_ligneecriture;
CREATE TRIGGER trg_ligne_exercice_cloture
    BEFORE INSERT OR UPDATE OR DELETE ON comptabilite_ligneecriture
    FOR EACH ROW EXECUTE FUNCTION check_ligne_exercice_cloture();
"""

R9_EXERCICE_CLOTURE_DOWN = """
DROP TRIGGER IF EXISTS trg_exercice_cloture ON comptabilite_piececomptable;
DROP FUNCTION IF EXISTS check_exercice_cloture();
DROP TRIGGER IF EXISTS trg_ligne_exercice_cloture ON comptabilite_ligneecriture;
DROP FUNCTION IF EXISTS check_ligne_exercice_cloture();
"""


class Migration(migrations.Migration):
    dependencies = [
        ("comptabilite", "0003_pg_triggers"),
    ]
    operations = [
        migrations.RunSQL(R9_EXERCICE_CLOTURE, reverse_sql=R9_EXERCICE_CLOTURE_DOWN),
    ]
