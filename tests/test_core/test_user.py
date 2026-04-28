from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

User = get_user_model()


class TestUserModel(TestCase):
    """Tests sur le modèle User — utilise TestCase car User est dans le schema public."""

    def test_user_creation_avec_email(self):
        user = User.objects.create_user(
            email="test@example.com",
            password="motdepasse123",
        )
        assert user.email == "test@example.com"
        assert user.statut == "actif"
        assert user.is_staff is False

    def test_user_str(self):
        user = User.objects.create_user(
            email="alice@example.com",
            password="motdepasse123",
        )
        assert str(user) == "alice@example.com"

    def test_statut_choices_valid(self):
        user = User.objects.create_user(
            email="bob@example.com",
            password="motdepasse123",
            statut="suspendu",
        )
        assert user.statut == "suspendu"

    def test_statut_invalid_raises_validation_error(self):
        user = User.objects.create_user(
            email="charlie@example.com",
            password="motdepasse123",
            statut="invalide",
        )
        with self.assertRaises(ValidationError):
            user.full_clean()

    def test_username_field_is_email(self):
        assert User.USERNAME_FIELD == "email"

    def test_required_fields_empty(self):
        assert User.REQUIRED_FIELDS == []

    def test_is_2fa_enabled_false_without_totp_device(self):
        user = User.objects.create_user(
            email="no2fa@example.com",
            password="motdepasse123",
        )
        assert user.is_2fa_enabled is False
