from django_tenants.test.cases import TenantTestCase
from django.contrib.auth import get_user_model

User = get_user_model()


class TestUserModel(TenantTestCase):
    def test_user_creation_avec_email(self):
        user = User.objects.create_user(
            username="test@example.com",
            email="test@example.com",
            password="motdepasse123",
        )
        assert user.email == "test@example.com"
        assert user.statut == "actif"
        assert user.is_2fa_enabled is False

    def test_user_str(self):
        user = User.objects.create_user(
            username="alice@example.com",
            email="alice@example.com",
            password="motdepasse123",
        )
        assert str(user) == "alice@example.com"

    def test_statut_choices(self):
        user = User.objects.create_user(
            username="bob@example.com",
            email="bob@example.com",
            password="motdepasse123",
            statut="suspendu",
        )
        assert user.statut == "suspendu"

    def test_username_field_is_email(self):
        assert User.USERNAME_FIELD == "email"
