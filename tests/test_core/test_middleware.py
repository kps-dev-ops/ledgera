from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from apps.core.middleware import AuditContextMiddleware

User = get_user_model()


class TestAuditContextMiddleware(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.get_response = MagicMock(return_value=MagicMock(status_code=200))
        self.middleware = AuditContextMiddleware(self.get_response)

    def test_middleware_sans_utilisateur_authentifie(self):
        request = self.factory.get("/")
        request.user = MagicMock(is_authenticated=False)
        response = self.middleware(request)
        assert response.status_code == 200

    def test_middleware_avec_utilisateur_authentifie(self):
        user = User.objects.create_user(
            username="test@test.com", email="test@test.com", password="pass"
        )
        request = self.factory.get("/")
        request.user = user
        request.META["REMOTE_ADDR"] = "192.168.1.1"

        with patch("apps.core.middleware.connection") as mock_conn:
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
            mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
            response = self.middleware(request)

        assert response.status_code == 200
