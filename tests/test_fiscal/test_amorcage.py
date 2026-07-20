"""Amorcage des configurations fiscales d'une nouvelle societe.

Sans elles, les ecrans TVA / IS / AIB presentent un menu deroulant vide et aucune
declaration ne peut etre creee : c'est le symptome « il y a une societe mais pas de
donnees » constate en preproduction.
"""

from decimal import Decimal

from django.db import connection
from django_tenants.test.cases import TenantTestCase

from apps.comptabilite.models import CompteComptable, Journal
from apps.fiscal.amorcage import init_configurations_fiscales
from apps.fiscal.models import ConfigurationAIB, ConfigurationIS, ConfigurationTVA

COMPTES_SYSCOHADA = [
    ("4431", "TVA facturée sur ventes", 4),
    ("4451", "TVA récupérable sur immobilisations", 4),
    ("4452", "TVA récupérable sur achats", 4),
    ("4441", "État, TVA due", 4),
    ("4449", "État, crédit de TVA à reporter", 4),
    ("441", "État, impôt sur les bénéfices", 4),
    ("4492", "État, avances et acomptes versés sur impôts", 4),
    ("891", "Impôts sur les bénéfices de l'exercice", 8),
    ("521", "Banques locales", 5),
]
COMPTES_PCG = [
    ("44571", "TVA collectée", 4),
    ("44566", "TVA déductible", 4),
    ("44551", "TVA à décaisser", 4),
    ("44567", "Crédit de TVA à reporter", 4),
    ("695", "Impôts sur les bénéfices", 6),
    ("444", "État, impôt sur les bénéfices", 4),
]


class AmorcageTestBase(TenantTestCase):
    referentiel = "SYSCOHADA"
    comptes = COMPTES_SYSCOHADA

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.code = "TEST"
        tenant.raison_sociale = "Société de Test"
        tenant.pays = "BJ"
        tenant.devise = "XOF"
        tenant.referentiel = cls.referentiel
        return tenant

    def setUp(self):
        super().setUp()
        with connection.cursor() as c:
            c.execute("SET LOCAL app.user_id = 1")
            c.execute("SET LOCAL app.user_email = 'test@ledgera.app'")
            c.execute("SET LOCAL app.ip = '127.0.0.1'")
        for numero, libelle, classe in self.comptes:
            CompteComptable.objects.create(numero=numero, libelle=libelle, classe=classe)
        self.od = Journal.objects.create(code="OD", libelle="Opérations diverses", type_journal="OD")
        self.societe = self.tenant


class TestSyscohada(AmorcageTestBase):
    def test_cree_les_trois_configurations(self):
        rapport = init_configurations_fiscales(self.societe)

        tva = ConfigurationTVA.objects.get()
        assert tva.compte_tva_due.numero == "4441"
        assert tva.compte_credit_tva.numero == "4449"
        assert set(tva.comptes_collectee.values_list("numero", flat=True)) == {"4431"}
        assert set(tva.comptes_deductible.values_list("numero", flat=True)) == {"4452", "4451"}

        impot = ConfigurationIS.objects.get()
        assert impot.taux == Decimal("30.00")  # taux beninois
        assert impot.compte_charge_impot.numero == "891"
        assert impot.compte_dette_impot.numero == "441"

        aib = ConfigurationAIB.objects.get()
        assert aib.taux == Decimal("1.00")
        assert aib.compte_aib.numero == "4492"

        assert all("créée" in m for m in rapport.values()), rapport

    def test_est_idempotent(self):
        """Relancer l'amorcage ne doit pas dupliquer les configurations."""
        init_configurations_fiscales(self.societe)
        rapport = init_configurations_fiscales(self.societe)

        assert ConfigurationTVA.objects.count() == 1
        assert ConfigurationIS.objects.count() == 1
        assert ConfigurationAIB.objects.count() == 1
        assert all("déjà configurée" in m for m in rapport.values()), rapport

    def test_les_configurations_alimentent_les_menus_deroulants(self):
        """Le symptome d'origine : le formulaire de declaration proposait une liste vide."""
        from apps.fiscal.forms import DeclarationAIBForm, DeclarationPeriodeForm

        assert DeclarationPeriodeForm().fields["configuration"].queryset.count() == 0
        init_configurations_fiscales(self.societe)
        assert DeclarationPeriodeForm().fields["configuration"].queryset.count() == 1
        assert DeclarationAIBForm().fields["configuration"].queryset.count() == 1


class TestPcgFrancais(AmorcageTestBase):
    referentiel = "PCG"
    comptes = COMPTES_PCG

    def test_utilise_la_nomenclature_francaise(self):
        init_configurations_fiscales(self.societe)

        tva = ConfigurationTVA.objects.get()
        assert tva.compte_tva_due.numero == "44551"
        assert set(tva.comptes_collectee.values_list("numero", flat=True)) == {"44571"}

        assert ConfigurationIS.objects.get().taux == Decimal("25.00")  # taux francais

    def test_aucune_aib_hors_ohada(self):
        """L'AIB est un acompte propre a la fiscalite beninoise."""
        rapport = init_configurations_fiscales(self.societe)
        assert ConfigurationAIB.objects.count() == 0
        assert "sans objet" in rapport["AIB"]


class TestPlanIncomplet(AmorcageTestBase):
    comptes = [("4431", "TVA facturée", 4)]  # tout le reste manque

    def test_signale_les_comptes_absents_sans_interrompre(self):
        """Une societe peut utiliser un plan sur mesure : l'absence d'un compte doit
        etre signalee, pas faire echouer tout l'amorcage."""
        rapport = init_configurations_fiscales(self.societe)

        assert ConfigurationTVA.objects.count() == 0
        assert "4441" in rapport["TVA"] and "absents" in rapport["TVA"]
        assert "absents" in rapport["IS"]

    def test_sans_journal_od_rien_n_est_cree(self):
        Journal.objects.filter(code="OD").delete()
        rapport = init_configurations_fiscales(self.societe)
        assert "Journal" in rapport["tout"]
        assert ConfigurationTVA.objects.count() == 0
