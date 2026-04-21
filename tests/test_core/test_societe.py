from django_tenants.test.cases import TenantTestCase
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from apps.core.models import SocieteMembership
from apps.tenants.models import Societe

User = get_user_model()


class TestSocieteMembership(TenantTestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="comptable@kps.bj",
            password="pass",
        )
        self.societe = Societe.objects.get(schema_name=self.tenant.schema_name)

    def test_membership_creation(self):
        membership = SocieteMembership.objects.create(
            user=self.user,
            societe=self.societe,
            role="comptable_junior",
        )
        assert membership.actif is True
        assert membership.role == "comptable_junior"

    def test_membership_str(self):
        m = SocieteMembership.objects.create(
            user=self.user, societe=self.societe, role="admin"
        )
        assert "comptable@kps.bj" in str(m)
        assert "admin" in str(m)

    def test_un_seul_role_par_utilisateur_par_societe(self):
        """Un user ne peut avoir qu'un seul membership par société (unique_together)."""
        SocieteMembership.objects.create(
            user=self.user, societe=self.societe, role="comptable_junior"
        )
        with self.assertRaises(IntegrityError):
            SocieteMembership.objects.create(
                user=self.user, societe=self.societe, role="admin"
            )

    def test_role_choices_valides(self):
        """Vérifie que les 5 rôles sont bien définis dans les choices."""
        valid_roles = ["admin", "comptable_senior", "comptable_junior", "daf_lecture", "auditeur"]
        assert [r[0] for r in SocieteMembership.ROLE_CHOICES] == valid_roles
