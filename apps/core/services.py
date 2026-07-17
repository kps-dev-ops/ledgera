from django_tenants.utils import tenant_context

from apps.referentiels.models import PlanComptableType
from apps.tenants.models import Domain, Societe


def provisionner_societe(*, code, schema_name, raison_sociale, pays, devise, referentiel,
                         plan_code, domaine=None, annee_exercice=2026) -> Societe:
    """Crée (idempotent) une société + son domaine et initialise, dans son schema, le
    plan de comptes, les journaux par défaut et l'exercice courant.

    Le domaine est optionnel et non routant : le routage multi-tenant se fait par
    utilisateur connecté (cf. TenantSessionMiddleware). Il reste requis techniquement
    par django-tenants (TENANT_DOMAIN_MODEL) ; à défaut, un domaine local est dérivé
    du schema_name.
    """
    plan = PlanComptableType.objects.filter(code=plan_code).first()
    if plan is None:
        raise ValueError(
            f"Plan de comptes type '{plan_code}' introuvable. "
            f"Chargez-le d'abord (ex. manage.py charger_plan_pcg)."
        )
    domaine = domaine or f"{schema_name}.local"
    societe, _ = Societe.objects.get_or_create(
        code=code,
        defaults={
            "schema_name": schema_name, "raison_sociale": raison_sociale, "pays": pays,
            "devise": devise, "referentiel": referentiel, "plan_comptes_type": plan,
        },
    )
    Domain.objects.get_or_create(domain=domaine, defaults={"tenant": societe, "is_primary": True})

    from apps.comptabilite.services import (
        init_exercice_courant,
        init_journaux_par_defaut,
        init_plan_comptable_pour_societe,
    )

    with tenant_context(societe):
        init_plan_comptable_pour_societe(societe)
        init_journaux_par_defaut()
        init_exercice_courant(annee_exercice)
    return societe
