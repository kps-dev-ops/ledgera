from django_tenants.test.cases import TenantTestCase
from django.contrib.auth import get_user_model
from apps.core.models import SocieteMembership
from apps.tenants.models import Societe

User = get_user_model()


class TestSocieteMembership(TenantTestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="comptable@kps.bj",
            email="comptable@kps.bj",
            password="pass",
        )

    def test_membership_creation(self):
        societe = Societe.objects.get(schema_name=self.tenant.schema_name)
        membership = SocieteMembership.objects.create(
            user=self.user,
            societe=societe,
            role="comptable_junior",
        )
        assert membership.actif is True
        assert membership.role == "comptable_junior"

    def test_membership_role_choices_valides(self):
        valid_roles = ["admin", "comptable_senior", "comptable_junior", "daf_lecture", "auditeur"]
        societe = Societe.objects.get(schema_name=self.tenant.schema_name)
        for role in valid_roles:
            m = SocieteMembership.objects.create(
                user=self.user, societe=societe, role=role
            )
            assert m.role == role
            m.delete()

    def test_membership_str(self):
        societe = Societe.objects.get(schema_name=self.tenant.schema_name)
        m = SocieteMembership.objects.create(
            user=self.user, societe=societe, role="admin"
        )
        assert "comptable@kps.bj" in str(m)
        assert "admin" in str(m)
