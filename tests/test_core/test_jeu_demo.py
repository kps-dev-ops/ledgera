"""Jeu de données de démonstration (cahier §7).

Son intérêt n'est pas d'exister mais d'être COHÉRENT : les écritures doivent passer
les triggers PostgreSQL (R1 équilibre, R5 dates, R7 tiers sur compte collectif), et
chaque écran doit avoir de la matière. Un jeu de démonstration faux se remarque
immédiatement en démonstration client — d'où ces vérifications comptables.
"""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command
from django.db.models import Sum
from django_tenants.utils import tenant_context

from apps.core.models import SocieteMembership
from apps.core.services import provisionner_societe
from apps.referentiels.services import charger_plan_depuis_fichier

User = get_user_model()


@pytest.fixture
def societe_demo(db):
    charger_plan_depuis_fichier("syscohada_2017.json")
    societe = provisionner_societe(
        code="DEMO", schema_name="demo_soc", raison_sociale="Demo SARL", pays="BJ",
        devise="XOF", referentiel="SYSCOHADA", plan_code="SYSCOHADA_2017",
    )
    u = User.objects.create_user(username="demo@x.fr", email="demo@x.fr", password="x")
    SocieteMembership.objects.create(user=u, societe=societe, role="admin", actif=True)
    return societe


@pytest.mark.django_db
def test_le_jeu_de_demo_peuple_tous_les_modules(societe_demo):
    call_command("jeu_demo", "--mois", "3")

    from apps.banque.models import CompteBancaire, LigneReleve
    from apps.comptabilite.models import PieceComptable
    from apps.fiscal.models import DeclarationAIB, DeclarationIS, DeclarationTVA
    from apps.immobilisations.models import Dotation, Immobilisation
    from apps.tiers.models import Tiers

    with tenant_context(societe_demo):
        assert Tiers.objects.filter(type_tiers="CLIENT").count() == 4
        assert Tiers.objects.filter(type_tiers="FOURNISSEUR").count() == 4
        assert PieceComptable.objects.count() > 0
        assert Immobilisation.objects.count() == 4
        assert Dotation.objects.count() > 0
        assert CompteBancaire.objects.count() == 1
        assert LigneReleve.objects.count() > 0
        assert DeclarationTVA.objects.count() == 2
        assert DeclarationIS.objects.count() == 1
        assert DeclarationAIB.objects.count() == 1


@pytest.mark.django_db
def test_toutes_les_pieces_sont_validees_et_equilibrees(societe_demo):
    """R1 : sans équilibre, les états sont faux et la démonstration se retourne
    contre nous."""
    call_command("jeu_demo", "--mois", "3")

    from apps.comptabilite.models import PieceComptable

    with tenant_context(societe_demo):
        assert not PieceComptable.objects.filter(statut="BROUILLARD").exists()
        for piece in PieceComptable.objects.all():
            totaux = piece.lignes.aggregate(d=Sum("debit"), c=Sum("credit"))
            assert totaux["d"] == totaux["c"], f"{piece.reference} déséquilibrée"
            assert piece.numero is not None, f"{piece.reference} sans numéro (R4)"


@pytest.mark.django_db
def test_la_balance_generale_est_equilibree(societe_demo):
    """Le contrôle qu'un comptable fait en premier."""
    call_command("jeu_demo", "--mois", "3")

    from apps.comptabilite.models import LigneEcriture

    with tenant_context(societe_demo):
        totaux = LigneEcriture.objects.filter(piece__statut="VALIDEE").aggregate(
            d=Sum("debit"), c=Sum("credit")
        )
        assert totaux["d"] == totaux["c"] != Decimal("0.00")


@pytest.mark.django_db
def test_les_comptes_collectifs_portent_toujours_un_tiers(societe_demo):
    """R7 : une écriture sur 411/401 sans tiers rend la balance auxiliaire fausse."""
    call_command("jeu_demo", "--mois", "3")

    from apps.comptabilite.models import LigneEcriture

    with tenant_context(societe_demo):
        orphelines = LigneEcriture.objects.filter(
            compte__collectif_tiers=True, tiers__isnull=True
        )
        assert not orphelines.exists()


@pytest.mark.django_db
def test_relance_ne_duplique_pas_les_pieces(societe_demo):
    """La commande complète, elle n'écrase pas : R3 interdit de supprimer une pièce
    validée, il n'existe donc aucune remise à zéro. La relance doit être sans effet."""
    call_command("jeu_demo", "--mois", "2")
    from apps.comptabilite.models import PieceComptable
    from apps.tiers.models import Tiers

    with tenant_context(societe_demo):
        avant = PieceComptable.objects.count()

    call_command("jeu_demo", "--mois", "2")

    with tenant_context(societe_demo):
        assert PieceComptable.objects.count() == avant
        assert Tiers.objects.count() == 8


@pytest.mark.django_db
def test_relance_avec_plus_de_mois_complete_sans_toucher_a_l_existant(societe_demo):
    call_command("jeu_demo", "--mois", "2")
    from apps.comptabilite.models import PieceComptable

    with tenant_context(societe_demo):
        avant = set(PieceComptable.objects.values_list("reference", flat=True))

    call_command("jeu_demo", "--mois", "4")

    with tenant_context(societe_demo):
        apres = set(PieceComptable.objects.values_list("reference", flat=True))
    assert avant < apres, "les mois supplémentaires n'ont pas été ajoutés"


@pytest.mark.django_db
def test_refus_explicite_sans_administrateur_habilite(db):
    """Une pièce doit avoir un auteur : mieux vaut un message clair qu'un plantage."""
    charger_plan_depuis_fichier("syscohada_2017.json")
    provisionner_societe(
        code="VIDE", schema_name="vide_soc", raison_sociale="Vide SARL", pays="BJ",
        devise="XOF", referentiel="SYSCOHADA", plan_code="SYSCOHADA_2017",
    )
    with pytest.raises(CommandError, match="assigner_societe"):
        call_command("jeu_demo")


@pytest.mark.django_db
def test_les_ecrans_affichent_reellement_les_donnees(client, societe_demo):
    """Le but recherche : « je veux voir des donnees partout ». Peupler la base ne
    suffit pas — encore faut-il que les ecrans les restituent."""
    from django.urls import reverse

    call_command("jeu_demo", "--mois", "3")
    client.force_login(User.objects.get(email="demo@x.fr"))

    # Ecran → fragment qui prouve que des donnees sont affichees, et non un etat vide.
    attendus = {
        "comptabilite:piece_list": "DEMO-VT-",
        "tiers:tiers_list": "SOBEBRA",
        "etats:balance": "7011",
        "etats:grand_livre": "4111",
        "immobilisations:immo_list": "Toyota Hilux",
        "banque:compte_list": "Compte courant BOA",
        "fiscal:declaration_list": "18",  # taux de TVA appliqué
    }
    for nom, fragment in attendus.items():
        html = client.get(reverse(nom)).content.decode()
        assert fragment in html, f"{nom} : « {fragment} » absent — l'écran semble vide"

    # Aucun ecran ne doit afficher son etat vide alors que la base est peuplee.
    for nom in ("comptabilite:piece_list", "tiers:tiers_list", "immobilisations:immo_list"):
        html = client.get(reverse(nom)).content.decode()
        assert "Aucune pièce" not in html and "Aucun tiers" not in html
