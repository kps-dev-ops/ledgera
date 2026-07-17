from django.db import connection
from django.shortcuts import redirect

from .permissions import permissions_du_role

CHEMINS_LIBRES = ("/admin/", "/accounts/", "/static/", "/media/", "/__reload__/", "/aucune-societe/")


class TenantSessionMiddleware:
    """Sélectionne le schema PG de la société active depuis l'utilisateur connecté et sa
    session — remplace le routage par domaine de django-tenants.

    Sécurité (R8) : la société mémorisée en session est revalidée à CHAQUE requête contre
    les habilitations actives de l'utilisateur. Une session trafiquée ne donne accès à rien.
    Doit être placé APRÈS AuthenticationMiddleware (il lui faut request.user).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from apps.core.models import SocieteMembership

        connection.set_schema_to_public()
        request.tenant = None
        request.societes_disponibles = []
        request.role_societe = None
        request.permissions = frozenset()

        if request.user.is_authenticated:
            memberships = list(
                SocieteMembership.objects.filter(user=request.user, actif=True).select_related("societe")
            )
            request.societes_disponibles = [m.societe for m in memberships]
            membership = self._resoudre_membership(request, memberships)
            if membership is not None:
                connection.set_tenant(membership.societe)
                request.tenant = membership.societe
                request.role_societe = membership.role
                request.permissions = permissions_du_role(membership.role)
            elif not request.path.startswith(CHEMINS_LIBRES):
                return redirect("aucune_societe")

        return self.get_response(request)

    @staticmethod
    def _resoudre_membership(request, memberships):
        """Membership de la société en session si habilitée, sinon le premier, sinon None."""
        autorises = {m.societe.pk: m for m in memberships}
        sid = request.session.get("societe_id")
        if sid in autorises:
            return autorises[sid]
        if memberships:
            membership = memberships[0]
            request.session["societe_id"] = membership.societe.pk
            return membership
        return None


def get_client_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "0.0.0.0")


class AuditContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            with connection.cursor() as c:
                c.execute(
                    "SET LOCAL app.user_id = %s; "
                    "SET LOCAL app.user_email = %s; "
                    "SET LOCAL app.ip = %s;",
                    [str(request.user.id), request.user.email, get_client_ip(request)],
                )
        return self.get_response(request)
