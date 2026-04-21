from django.contrib.auth import get_user_model
from django.db import connection
from django_tenants.test.cases import TenantTestCase

from apps.audit.models import JournalAudit

User = get_user_model()


class TestAuditTriggers(TenantTestCase):
    def setUp(self):
        with connection.cursor() as c:
            c.execute("SET LOCAL app.user_id = 1")
            c.execute("SET LOCAL app.user_email = 'test@ledgera.app'")
            c.execute("SET LOCAL app.ip = '127.0.0.1'")

    def test_journal_audit_insert_only(self):
        """Vérifie que l'admin refuse la suppression (has_delete_permission=False)."""
        from django.contrib.admin.sites import AdminSite

        from apps.audit.admin import JournalAuditAdmin

        JournalAudit.objects.create(
            action="TEST",
            table_cible="test_table",
            enregistrement_id=1,
            utilisateur_id=1,
            utilisateur_email="test@ledgera.app",
            ip_adresse="127.0.0.1",
        )
        site = AdminSite()
        admin_instance = JournalAuditAdmin(JournalAudit, site)
        assert admin_instance.has_delete_permission(request=None) is False
        assert admin_instance.has_change_permission(request=None) is False
        assert admin_instance.has_add_permission(request=None) is False

    def test_journal_audit_fields(self):
        entry = JournalAudit.objects.create(
            action="INSERT",
            table_cible="comptabilite_piececomptable",
            enregistrement_id=42,
            utilisateur_id=1,
            utilisateur_email="comptable@kps.bj",
            valeurs_apres={"id": 42, "statut": "BROUILLARD"},
            ip_adresse="10.0.0.1",
        )
        assert entry.action == "INSERT"
        assert entry.valeurs_apres["statut"] == "BROUILLARD"
