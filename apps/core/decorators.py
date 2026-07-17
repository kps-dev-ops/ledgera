from functools import wraps

from django.core.exceptions import PermissionDenied

from .permissions import a_permission


def exige_permission(permission: str, methodes: tuple[str, ...] | None = None):
    """Refuse (403) si le rôle sur la société active n'a pas la permission.

    `methodes` : si fourni, le contrôle ne s'applique qu'à ces méthodes HTTP
    (ex. ("POST",)) — la lecture reste ouverte aux rôles consultants.
    """

    def decorateur(vue):
        @wraps(vue)
        def _wrapper(request, *args, **kwargs):
            if methodes is None or request.method in methodes:
                if not a_permission(getattr(request, "role_societe", None), permission):
                    raise PermissionDenied(f"Permission requise : {permission}")
            return vue(request, *args, **kwargs)

        return _wrapper

    return decorateur


class PermissionRequiseMixin:
    """Mixin CBV : définir `permission_requise`."""

    permission_requise: str | None = None

    def dispatch(self, request, *args, **kwargs):
        if not a_permission(getattr(request, "role_societe", None), self.permission_requise):
            raise PermissionDenied(f"Permission requise : {self.permission_requise}")
        return super().dispatch(request, *args, **kwargs)
