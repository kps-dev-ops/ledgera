"""Matrice d'autorisations par rôle — source unique de vérité (cahier §4.1 / archi §6.2).

Fail-closed : un rôle absent, inconnu, ou une permission inconnue → aucun droit.
"""

ADMIN = "admin"
SENIOR = "comptable_senior"
JUNIOR = "comptable_junior"
DAF = "daf_lecture"
AUDITEUR = "auditeur"

PERMISSIONS: dict[str, frozenset[str]] = {
    "saisir_brouillard": frozenset({ADMIN, SENIOR, JUNIOR}),
    "valider_piece": frozenset({ADMIN, SENIOR}),
    "cloturer_exercice": frozenset({ADMIN}),
    "consulter_etats": frozenset({ADMIN, SENIOR, JUNIOR, DAF, AUDITEUR}),
    "editer_declarations": frozenset({ADMIN, SENIOR}),
    "parametrer_plan_comptes": frozenset({ADMIN}),
    "consulter_audit": frozenset({ADMIN, AUDITEUR}),
}


def a_permission(role: str | None, permission: str) -> bool:
    """True si le rôle possède la permission. Fail-closed."""
    return role in PERMISSIONS.get(permission, frozenset())


def permissions_du_role(role: str | None) -> frozenset[str]:
    """Ensemble des permissions d'un rôle (vide si rôle absent/inconnu)."""
    if not role:
        return frozenset()
    return frozenset(p for p, roles in PERMISSIONS.items() if role in roles)
