import pytest
from django.core.management import CommandError, call_command
from django.contrib.auth import get_user_model
from apps.core.models import SocieteMembership
from apps.core.services import provisionner_societe
from apps.referentiels.services import charger_plan_depuis_fichier

User = get_user_model()

def _societe(code="KPS_BJ", schema="kps_bj"):
    charger_plan_depuis_fichier("syscohada_2017.json")
    return provisionner_societe(code=code, schema_name=schema, raison_sociale="KPS",
        pays="BJ", devise="XOF", referentiel="SYSCOHADA", plan_code="SYSCOHADA_2017")

@pytest.mark.django_db
def test_assigne_et_reexecute():
    s = _societe()
    u = User.objects.create_user(username="a@x.fr", email="a@x.fr", password="x")
    call_command("assigner_societe", "--email", "a@x.fr", "--role", "admin")
    m = SocieteMembership.objects.get(user=u, societe=s)
    assert m.role == "admin" and m.actif
    # re-executer doit corriger le role, pas planter sur l'unicite
    call_command("assigner_societe", "--email", "a@x.fr", "--role", "auditeur")
    m.refresh_from_db(); assert m.role == "auditeur"

@pytest.mark.django_db
def test_superuser_flag():
    _societe()
    User.objects.create_user(username="b@x.fr", email="b@x.fr", password="x")
    call_command("assigner_societe", "--email", "b@x.fr", "--superuser")
    u = User.objects.get(email="b@x.fr")
    assert u.is_staff and u.is_superuser

@pytest.mark.django_db
def test_email_inconnu():
    _societe()
    with pytest.raises(CommandError, match="Aucun compte"):
        call_command("assigner_societe", "--email", "fantome@x.fr")

@pytest.mark.django_db
def test_aucune_societe():
    User.objects.create_user(username="c@x.fr", email="c@x.fr", password="x")
    with pytest.raises(CommandError, match="Aucune societe"):
        call_command("assigner_societe", "--email", "c@x.fr")
