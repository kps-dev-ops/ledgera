from django.db import migrations

# R1 + R3 : équilibre strict si validée + protection des pièces validées
R1_R3_PIECE = """
CREATE OR REPLACE FUNCTION check_piece_validee() RETURNS trigger AS $body$
BEGIN
    -- R3 : protection contre modification d'une pièce déjà validée
    IF TG_OP = 'UPDATE' AND OLD.statut = 'VALIDEE' THEN
        IF NEW.statut NOT IN ('VALIDEE', 'EXTOURNEE') THEN
            RAISE EXCEPTION 'R3 : modification interdite sur piece validee (id=%)', OLD.id;
        END IF;
        IF NEW.date_piece <> OLD.date_piece
           OR NEW.libelle <> OLD.libelle
           OR NEW.total_debit <> OLD.total_debit
           OR NEW.total_credit <> OLD.total_credit
           OR NEW.journal_id <> OLD.journal_id
           OR NEW.exercice_id <> OLD.exercice_id
           OR NEW.numero IS DISTINCT FROM OLD.numero THEN
            RAISE EXCEPTION 'R3 : seuls statut/extourne modifiables sur piece validee (id=%)', OLD.id;
        END IF;
    END IF;
    -- R1 : équilibre strict si la pièce est ou devient VALIDEE
    IF TG_OP IN ('INSERT', 'UPDATE') AND NEW.statut = 'VALIDEE'
       AND NEW.total_debit <> NEW.total_credit THEN
        RAISE EXCEPTION 'R1 : piece non equilibree (debit=% / credit=%)',
                        NEW.total_debit, NEW.total_credit;
    END IF;
    RETURN NEW;
END;
$body$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION check_piece_delete() RETURNS trigger AS $body$
BEGIN
    IF OLD.statut = 'VALIDEE' THEN
        RAISE EXCEPTION 'R3 : suppression interdite sur piece validee (id=%)', OLD.id;
    END IF;
    RETURN OLD;
END;
$body$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_piece_check ON comptabilite_piececomptable;
CREATE TRIGGER trg_piece_check
    BEFORE INSERT OR UPDATE ON comptabilite_piececomptable
    FOR EACH ROW EXECUTE FUNCTION check_piece_validee();

DROP TRIGGER IF EXISTS trg_piece_delete ON comptabilite_piececomptable;
CREATE TRIGGER trg_piece_delete
    BEFORE DELETE ON comptabilite_piececomptable
    FOR EACH ROW EXECUTE FUNCTION check_piece_delete();
"""

R1_R3_PIECE_DOWN = """
DROP TRIGGER IF EXISTS trg_piece_check ON comptabilite_piececomptable;
DROP TRIGGER IF EXISTS trg_piece_delete ON comptabilite_piececomptable;
DROP FUNCTION IF EXISTS check_piece_validee();
DROP FUNCTION IF EXISTS check_piece_delete();
"""

# R5 : date_piece dans l'exercice
R5_DATE_EXERCICE = """
CREATE OR REPLACE FUNCTION check_date_exercice() RETURNS trigger AS $body$
DECLARE
    d_debut DATE;
    d_fin DATE;
BEGIN
    SELECT date_debut, date_fin INTO d_debut, d_fin
    FROM comptabilite_exercice WHERE id = NEW.exercice_id;
    IF NEW.date_piece < d_debut OR NEW.date_piece > d_fin THEN
        RAISE EXCEPTION 'R5 : date_piece % hors exercice [% .. %]',
                        NEW.date_piece, d_debut, d_fin;
    END IF;
    RETURN NEW;
END;
$body$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_date_exercice ON comptabilite_piececomptable;
CREATE TRIGGER trg_date_exercice
    BEFORE INSERT OR UPDATE ON comptabilite_piececomptable
    FOR EACH ROW EXECUTE FUNCTION check_date_exercice();
"""

R5_DATE_EXERCICE_DOWN = """
DROP TRIGGER IF EXISTS trg_date_exercice ON comptabilite_piececomptable;
DROP FUNCTION IF EXISTS check_date_exercice();
"""

# R7 : tiers obligatoire si compte collectif, interdit sinon
R7_TIERS_COLLECTIF = """
CREATE OR REPLACE FUNCTION check_tiers_collectif() RETURNS trigger AS $body$
DECLARE collectif BOOLEAN;
BEGIN
    SELECT collectif_tiers INTO collectif
    FROM comptabilite_comptecomptable WHERE id = NEW.compte_id;
    IF collectif AND NEW.tiers_id IS NULL THEN
        RAISE EXCEPTION 'R7 : tiers obligatoire sur compte collectif (compte_id=%)', NEW.compte_id;
    END IF;
    IF NOT collectif AND NEW.tiers_id IS NOT NULL THEN
        RAISE EXCEPTION 'R7 : tiers interdit sur compte non collectif (compte_id=%)', NEW.compte_id;
    END IF;
    RETURN NEW;
END;
$body$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_tiers_collectif ON comptabilite_ligneecriture;
CREATE TRIGGER trg_tiers_collectif
    BEFORE INSERT OR UPDATE ON comptabilite_ligneecriture
    FOR EACH ROW EXECUTE FUNCTION check_tiers_collectif();
"""

R7_TIERS_COLLECTIF_DOWN = """
DROP TRIGGER IF EXISTS trg_tiers_collectif ON comptabilite_ligneecriture;
DROP FUNCTION IF EXISTS check_tiers_collectif();
"""

# R2 : période verrouillée bloque la saisie
R2_PERIODE_VERROUILLEE = """
CREATE OR REPLACE FUNCTION check_periode_ouverte() RETURNS trigger AS $body$
DECLARE p_statut TEXT;
BEGIN
    SELECT statut INTO p_statut
    FROM comptabilite_periode
    WHERE exercice_id = NEW.exercice_id
      AND mois = EXTRACT(MONTH FROM NEW.date_piece)::int;
    IF p_statut IS NULL THEN
        RETURN NEW;  -- période non encore créée : autorisé (créée à la volée)
    END IF;
    IF p_statut IN ('VERROUILLEE', 'CLOTUREE') THEN
        RAISE EXCEPTION 'R2 : periode % du mois % verrouillee/cloturee',
                        NEW.exercice_id, EXTRACT(MONTH FROM NEW.date_piece)::int;
    END IF;
    RETURN NEW;
END;
$body$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_periode_ouverte ON comptabilite_piececomptable;
CREATE TRIGGER trg_periode_ouverte
    BEFORE INSERT OR UPDATE ON comptabilite_piececomptable
    FOR EACH ROW EXECUTE FUNCTION check_periode_ouverte();
"""

R2_PERIODE_VERROUILLEE_DOWN = """
DROP TRIGGER IF EXISTS trg_periode_ouverte ON comptabilite_piececomptable;
DROP FUNCTION IF EXISTS check_periode_ouverte();
"""

# R4 : pièce VALIDEE doit avoir un numéro non NULL
R4_NUMEROTATION = """
CREATE OR REPLACE FUNCTION check_numero_validee() RETURNS trigger AS $body$
BEGIN
    IF NEW.statut = 'VALIDEE' AND NEW.numero IS NULL THEN
        RAISE EXCEPTION 'R4 : piece validee sans numero (id=%)', NEW.id;
    END IF;
    RETURN NEW;
END;
$body$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_numero_validee ON comptabilite_piececomptable;
CREATE TRIGGER trg_numero_validee
    BEFORE INSERT OR UPDATE ON comptabilite_piececomptable
    FOR EACH ROW EXECUTE FUNCTION check_numero_validee();
"""

R4_NUMEROTATION_DOWN = """
DROP TRIGGER IF EXISTS trg_numero_validee ON comptabilite_piececomptable;
DROP FUNCTION IF EXISTS check_numero_validee();
"""


class Migration(migrations.Migration):
    dependencies = [
        ("comptabilite", "0002_initial"),
        ("tiers", "0001_initial"),
    ]
    operations = [
        migrations.RunSQL(R1_R3_PIECE, reverse_sql=R1_R3_PIECE_DOWN),
        migrations.RunSQL(R5_DATE_EXERCICE, reverse_sql=R5_DATE_EXERCICE_DOWN),
        migrations.RunSQL(R7_TIERS_COLLECTIF, reverse_sql=R7_TIERS_COLLECTIF_DOWN),
        migrations.RunSQL(R2_PERIODE_VERROUILLEE, reverse_sql=R2_PERIODE_VERROUILLEE_DOWN),
        migrations.RunSQL(R4_NUMEROTATION, reverse_sql=R4_NUMEROTATION_DOWN),
    ]
