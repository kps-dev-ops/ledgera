import pytest

from apps.core.permissions import PERMISSIONS, a_permission, permissions_du_role

MATRICE = {
    "saisir_brouillard": {"admin", "comptable_senior", "comptable_junior"},
    "valider_piece": {"admin", "comptable_senior"},
    "cloturer_exercice": {"admin"},
    "consulter_etats": {"admin", "comptable_senior", "comptable_junior", "daf_lecture", "auditeur"},
    "editer_declarations": {"admin", "comptable_senior"},
    "parametrer_plan_comptes": {"admin"},
    "consulter_audit": {"admin", "auditeur"},
}
TOUS_ROLES = ["admin", "comptable_senior", "comptable_junior", "daf_lecture", "auditeur"]


def test_catalogue_couvre_exactement_la_matrice():
    assert set(PERMISSIONS) == set(MATRICE)


@pytest.mark.parametrize("permission,roles_attendus", MATRICE.items())
def test_matrice_par_permission(permission, roles_attendus):
    for role in TOUS_ROLES:
        attendu = role in roles_attendus
        assert a_permission(role, permission) is attendu, f"{role} / {permission}"


def test_role_absent_ou_inconnu_na_aucune_permission():
    for permission in MATRICE:
        assert a_permission(None, permission) is False
        assert a_permission("role_bidon", permission) is False
    assert permissions_du_role(None) == frozenset()
    assert permissions_du_role("role_bidon") == frozenset()


def test_permission_inconnue_refusee():
    assert a_permission("admin", "permission_inexistante") is False


def test_permissions_du_role():
    assert permissions_du_role("auditeur") == frozenset({"consulter_etats", "consulter_audit"})
    assert permissions_du_role("daf_lecture") == frozenset({"consulter_etats"})
    assert permissions_du_role("admin") == frozenset(MATRICE)
