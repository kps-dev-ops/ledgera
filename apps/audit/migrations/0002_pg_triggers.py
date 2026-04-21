from django.db import migrations


REVOKE_SQL = """
REVOKE UPDATE, DELETE ON audit_journalaudit FROM PUBLIC;
"""

GRANT_SQL = """
GRANT INSERT, SELECT ON audit_journalaudit TO PUBLIC;
"""

LOG_AUDIT_FUNCTION = """
CREATE OR REPLACE FUNCTION log_audit() RETURNS trigger AS $$
DECLARE
    v_user_id INT;
    v_user_email TEXT;
    v_ip TEXT;
BEGIN
    BEGIN
        v_user_id := current_setting('app.user_id', true)::int;
    EXCEPTION WHEN OTHERS THEN
        v_user_id := 0;
    END;
    v_user_email := coalesce(current_setting('app.user_email', true), 'system');
    v_ip := coalesce(current_setting('app.ip', true), '0.0.0.0');

    INSERT INTO audit_journalaudit(
        horodatage, utilisateur_id, utilisateur_email,
        action, table_cible, enregistrement_id,
        valeurs_avant, valeurs_apres, ip_adresse
    ) VALUES (
        NOW(),
        v_user_id,
        v_user_email,
        TG_OP,
        TG_TABLE_NAME,
        COALESCE(NEW.id, OLD.id),
        CASE WHEN TG_OP IN ('UPDATE','DELETE') THEN row_to_json(OLD) ELSE NULL END,
        CASE WHEN TG_OP IN ('INSERT','UPDATE') THEN row_to_json(NEW) ELSE NULL END,
        v_ip
    );
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
"""

DROP_LOG_AUDIT_FUNCTION = "DROP FUNCTION IF EXISTS log_audit() CASCADE;"


class Migration(migrations.Migration):

    dependencies = [
        ("audit", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(REVOKE_SQL, reverse_sql=migrations.RunSQL.noop),
        migrations.RunSQL(GRANT_SQL, reverse_sql=migrations.RunSQL.noop),
        migrations.RunSQL(LOG_AUDIT_FUNCTION, reverse_sql=DROP_LOG_AUDIT_FUNCTION),
    ]
