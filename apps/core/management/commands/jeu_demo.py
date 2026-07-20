"""Jeu de données de démonstration (cahier des charges §7).

Peuple une société avec un exercice complet et cohérent : tiers, factures d'achat et
de vente, règlements bancaires et caisse, immobilisations amorties, relevé bancaire
partiellement rapproché, déclarations fiscales. Tous les écrans ont ainsi de la
matière à afficher.

Les montants sont DÉTERMINISTES (aucun tirage aléatoire) : deux exécutions produisent
les mêmes chiffres, ce qui rend la démonstration reproductible et le test possible.
"""

from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django_tenants.utils import tenant_context

from apps.comptabilite.models import CompteComptable, Exercice, Journal, LigneEcriture, PieceComptable
from apps.comptabilite.services import valider_piece
from apps.core.models import SocieteMembership
from apps.tenants.models import Societe
from apps.tiers.models import Tiers

TVA = Decimal("0.18")  # taux normal au Bénin
CENT = Decimal("0.01")

CLIENTS = [
    ("C001", "SOBEBRA SA", "Cotonou"),
    ("C002", "Bénin Télécoms SA", "Cotonou"),
    ("C003", "Groupe Sifca", "Abidjan"),
    ("C004", "Pharmacie Camp Guézo", "Cotonou"),
]
FOURNISSEURS = [
    ("F001", "CIMBENIN SA", "Cotonou"),
    ("F002", "Total Énergies Bénin", "Cotonou"),
    ("F003", "SBEE", "Cotonou"),
    ("F004", "Bureautique Plus SARL", "Porto-Novo"),
]


def _ttc(ht: Decimal) -> tuple[Decimal, Decimal]:
    """Retourne (tva, ttc) arrondis au centime."""
    tva = (ht * TVA).quantize(CENT)
    return tva, ht + tva


class Command(BaseCommand):
    help = "Crée un jeu de données de démonstration complet dans une société."

    def add_arguments(self, parser):
        parser.add_argument("--societe", help="Code de la société. Facultatif s'il n'en existe qu'une.")
        parser.add_argument("--exercice", default=None, help="Code de l'exercice (défaut : le plus récent)")
        parser.add_argument("--mois", type=int, default=6, help="Nombre de mois à générer (défaut : 6)")
        # Pas d'option de remise à zéro : R3 interdit la suppression d'une pièce
        # validée, et c'est voulu — une écriture comptable validée est immuable. La
        # commande est donc idempotente : elle complète, elle n'écrase jamais. Pour
        # repartir de zéro, provisionner une nouvelle société.

    def handle(self, *args, **o):
        societe = self._resoudre_societe(o["societe"])
        with tenant_context(societe):
            self._poser_contexte_audit()
            exercice = self._resoudre_exercice(o["exercice"])
            user = self._resoudre_auteur(societe)
            self._verifier_prerequis()

            mois = max(1, min(12, o["mois"]))
            tiers = self._creer_tiers()
            self.stdout.write(self.style.SUCCESS(f"  • Tiers : {len(tiers)} clients et fournisseurs"))

            n_pieces = self._creer_flux(exercice, user, tiers, mois)
            self.stdout.write(self.style.SUCCESS(f"  • Écritures : {n_pieces} pièces validées sur {mois} mois"))

            n_immo = self._creer_immobilisations(exercice, user)
            self.stdout.write(self.style.SUCCESS(f"  • Immobilisations : {n_immo} fiches amorties"))

            resume_banque = self._creer_banque(exercice)
            self.stdout.write(self.style.SUCCESS(f"  • Banque : {resume_banque}"))

            resume_fiscal = self._creer_declarations(exercice, user)
            self.stdout.write(self.style.SUCCESS(f"  • Fiscal : {resume_fiscal}"))

        self.stdout.write(self.style.SUCCESS(f"\nJeu de démonstration prêt sur {societe.code}."))

    # ------------------------------------------------------------------ contexte

    def _resoudre_societe(self, code):
        societes = Societe.objects.exclude(schema_name="public")
        if code:
            societe = societes.filter(code=code).first()
            if societe is None:
                dispo = ", ".join(societes.values_list("code", flat=True)) or "(aucune)"
                raise CommandError(f"Société '{code}' introuvable. Disponibles : {dispo}")
            return societe
        if societes.count() == 0:
            raise CommandError("Aucune société. Lancez d'abord : manage.py bootstrap_tenant")
        if societes.count() > 1:
            dispo = ", ".join(societes.values_list("code", flat=True))
            raise CommandError(f"Plusieurs sociétés, précisez --societe. Disponibles : {dispo}")
        return societes.first()

    def _poser_contexte_audit(self):
        # Les triggers d'audit lisent ces variables de session. Hors requête HTTP elles
        # sont absentes : sans cela les écritures seraient tracées sans auteur.
        with connection.cursor() as c:
            c.execute("SET app.user_email = 'demo@ledgera.app'")
            c.execute("SET app.ip = '127.0.0.1'")

    def _resoudre_exercice(self, code):
        if code:
            ex = Exercice.objects.filter(code=code).first()
            if ex is None:
                dispo = ", ".join(Exercice.objects.values_list("code", flat=True)) or "(aucun)"
                raise CommandError(f"Exercice '{code}' introuvable. Disponibles : {dispo}")
            return ex
        ex = Exercice.objects.order_by("-date_debut").first()
        if ex is None:
            raise CommandError("Aucun exercice. Lancez d'abord : manage.py bootstrap_tenant")
        if ex.statut == "CLOTURE":
            raise CommandError(f"L'exercice {ex.code} est clôturé : aucune écriture ne peut y être ajoutée (R9).")
        return ex

    def _resoudre_auteur(self, societe):
        membership = (
            SocieteMembership.objects.filter(societe=societe, actif=True, role="admin")
            .select_related("user").first()
        )
        if membership is None:
            raise CommandError(
                "Aucun administrateur habilité sur cette société — les pièces doivent avoir un auteur.\n"
                "  manage.py assigner_societe --email <votre-email> --role admin"
            )
        return membership.user

    def _verifier_prerequis(self):
        journaux = set(Journal.objects.values_list("code", flat=True))
        manquants = {"ACH", "VTE", "BQ1", "CA", "OD"} - journaux
        if manquants:
            raise CommandError(f"Journaux absents : {', '.join(sorted(manquants))}. Lancez bootstrap_tenant.")
        comptes = set(CompteComptable.objects.values_list("numero", flat=True))
        requis = {"4111", "4011", "601", "7011", "706", "4431", "4452", "521", "571"}
        absents = requis - comptes
        if absents:
            raise CommandError(
                f"Comptes absents du plan : {', '.join(sorted(absents))}. Lancez bootstrap_tenant."
            )

    # ------------------------------------------------------------------ données

    def _creer_tiers(self):
        compte_client = CompteComptable.objects.get(numero="4111")
        compte_fournisseur = CompteComptable.objects.get(numero="4011")
        crees = []
        for lot, compte, type_tiers in (
            (CLIENTS, compte_client, "CLIENT"),
            (FOURNISSEURS, compte_fournisseur, "FOURNISSEUR"),
        ):
            for code, raison, ville in lot:
                tiers, _ = Tiers.objects.get_or_create(
                    code_auxiliaire=code,
                    defaults={
                        "type_tiers": type_tiers, "compte_collectif": compte,
                        "raison_sociale": raison, "ville": ville, "pays": "BJ",
                        "delai_reglement_jours": 30, "mode_reglement": "VIREMENT",
                    },
                )
                crees.append(tiers)
        return crees

    def _piece(self, *, journal, exercice, jour, reference, libelle, user, lignes):
        """Crée puis valide une pièce, sauf si sa référence existe déjà.

        `lignes` : (compte, tiers, libelle, debit, credit). Retourne None si la pièce
        était déjà là — c'est ce qui rend la commande rejouable sans doublon, alors
        qu'une pièce validée ne peut pas être supprimée (R3).
        """
        if PieceComptable.objects.filter(exercice=exercice, reference=reference).exists():
            return None
        with transaction.atomic():
            piece = PieceComptable.objects.create(
                journal=journal, exercice=exercice, date_piece=jour,
                reference=reference, libelle=libelle, statut="BROUILLARD", auteur=user,
            )
            for i, (compte, tiers, lib, debit, credit) in enumerate(lignes, start=1):
                LigneEcriture.objects.create(
                    piece=piece, numero_ligne=i, compte=compte, tiers=tiers, libelle=lib,
                    debit=debit, credit=credit, date_operation=jour,
                )
            return valider_piece(piece, user)

    def _creer_flux(self, exercice, user, tiers, nb_mois):
        c = {n: CompteComptable.objects.get(numero=n) for n in
             ("4111", "4011", "601", "7011", "706", "4431", "4452", "521", "571")}
        j = {code: Journal.objects.get(code=code) for code in ("ACH", "VTE", "BQ1", "CA")}
        clients = [t for t in tiers if t.type_tiers == "CLIENT"]
        fournisseurs = [t for t in tiers if t.type_tiers == "FOURNISSEUR"]
        annee = exercice.date_debut.year
        n = 0

        for m in range(1, nb_mois + 1):
            # --- Ventes : deux factures, montants croissants et distincts par mois
            for k in (0, 1):
                client = clients[(m + k) % len(clients)]
                ht = Decimal(1_000_000 + m * 50_000 + k * 250_000)
                tva, ttc = _ttc(ht)
                ref = f"DEMO-VT-{annee}{m:02d}{k}"
                cree = self._piece(
                    journal=j["VTE"], exercice=exercice, jour=date(annee, m, 5 + k * 10),
                    reference=ref, libelle=f"Facture {client.raison_sociale}", user=user,
                    lignes=[
                        (c["4111"], client, "Créance client", ttc, Decimal("0.00")),
                        (c["7011"], None, "Vente de marchandises", Decimal("0.00"), ht),
                        (c["4431"], None, "TVA collectée 18 %", Decimal("0.00"), tva),
                    ],
                )
                n += 1 if cree else 0

            # --- Achats : deux factures
            for k in (0, 1):
                fournisseur = fournisseurs[(m + k) % len(fournisseurs)]
                ht = Decimal(600_000 + m * 30_000 + k * 150_000)
                tva, ttc = _ttc(ht)
                cree = self._piece(
                    journal=j["ACH"], exercice=exercice, jour=date(annee, m, 8 + k * 10),
                    reference=f"DEMO-AC-{annee}{m:02d}{k}",
                    libelle=f"Achat {fournisseur.raison_sociale}", user=user,
                    lignes=[
                        (c["601"], None, "Achats de marchandises", ht, Decimal("0.00")),
                        (c["4452"], None, "TVA déductible 18 %", tva, Decimal("0.00")),
                        (c["4011"], fournisseur, "Dette fournisseur", Decimal("0.00"), ttc),
                    ],
                )
                n += 1 if cree else 0

            # --- Règlements du mois précédent : la trésorerie suit les factures
            if m > 1:
                client = clients[(m - 1) % len(clients)]
                _, ttc_client = _ttc(Decimal(1_000_000 + (m - 1) * 50_000))
                cree_e = self._piece(
                    journal=j["BQ1"], exercice=exercice, jour=date(annee, m, 12),
                    reference=f"DEMO-BQ-{annee}{m:02d}E",
                    libelle=f"Encaissement {client.raison_sociale}", user=user,
                    lignes=[
                        (c["521"], None, "Encaissement client", ttc_client, Decimal("0.00")),
                        (c["4111"], client, "Solde facture", Decimal("0.00"), ttc_client),
                    ],
                )
                fournisseur = fournisseurs[(m - 1) % len(fournisseurs)]
                _, ttc_fourn = _ttc(Decimal(600_000 + (m - 1) * 30_000))
                cree_d = self._piece(
                    journal=j["BQ1"], exercice=exercice, jour=date(annee, m, 15),
                    reference=f"DEMO-BQ-{annee}{m:02d}D",
                    libelle=f"Règlement {fournisseur.raison_sociale}", user=user,
                    lignes=[
                        (c["4011"], fournisseur, "Solde facture", ttc_fourn, Decimal("0.00")),
                        (c["521"], None, "Virement fournisseur", Decimal("0.00"), ttc_fourn),
                    ],
                )
                n += sum(1 for x in (cree_e, cree_d) if x is not None)

            # --- Vente au comptant en caisse
            ht_caisse = Decimal(100_000 + m * 10_000)
            tva_caisse, ttc_caisse = _ttc(ht_caisse)
            cree_ca = self._piece(
                journal=j["CA"], exercice=exercice, jour=date(annee, m, 20),
                reference=f"DEMO-CA-{annee}{m:02d}", libelle="Prestations au comptant", user=user,
                lignes=[
                    (c["571"], None, "Encaissement espèces", ttc_caisse, Decimal("0.00")),
                    (c["706"], None, "Services vendus", Decimal("0.00"), ht_caisse),
                    (c["4431"], None, "TVA collectée 18 %", Decimal("0.00"), tva_caisse),
                ],
            )
            n += 1 if cree_ca else 0
        return n

    def _creer_immobilisations(self, exercice, user):
        from apps.immobilisations.models import CategorieImmobilisation, Immobilisation
        from apps.immobilisations.services import generer_plan_amortissement

        categories = list(CategorieImmobilisation.objects.order_by("code"))
        if not categories:
            return 0
        annee = exercice.date_debut.year
        materiels = [
            ("Serveur Dell PowerEdge", Decimal("4500000.00")),
            ("Poste de travail x5", Decimal("2750000.00")),
            ("Mobilier de direction", Decimal("1800000.00")),
            ("Toyota Hilux double cabine", Decimal("18500000.00")),
        ]
        n = 0
        for i, (designation, cout) in enumerate(materiels):
            categorie = categories[i % len(categories)]
            acquisition = date(annee, 1, 15)
            immo, cree = Immobilisation.objects.get_or_create(
                code=f"DEMO-I{i + 1:03d}",
                defaults={
                    "designation": designation, "categorie": categorie,
                    "date_acquisition": acquisition, "date_mise_service": acquisition,
                    "cout_acquisition": cout, "duree": categorie.duree_defaut,
                    "mode_amortissement": categorie.mode_defaut,
                    "compte_immo": categorie.compte_immo,
                    "compte_amortissement": categorie.compte_amortissement,
                    "compte_dotation": categorie.compte_dotation,
                },
            )
            if cree:
                generer_plan_amortissement(immo)
                n += 1
        return n

    def _creer_banque(self, exercice):
        from apps.banque.models import CompteBancaire, LigneReleve
        from apps.banque.services import creer_releve_depuis_lignes, pointer_automatiquement

        compte, _ = CompteBancaire.objects.get_or_create(
            libelle="Compte courant BOA",
            defaults={
                "compte_comptable": CompteComptable.objects.get(numero="521"),
                "journal": Journal.objects.get(code="BQ1"),
                "banque_nom": "Bank Of Africa Bénin", "devise": "XOF",
                "solde_initial": Decimal("25000000.00"),
            },
        )
        annee = exercice.date_debut.year
        if compte.releves.exists():
            return f"compte {compte.libelle} (relevé déjà présent)"

        # Le relevé reprend les mouvements bancaires réels du mois, plus deux opérations
        # absentes de la comptabilité (frais, agios) : le rapprochement a ainsi de quoi
        # montrer à la fois des lignes pointées et des écarts à traiter.
        mouvements = LigneEcriture.objects.filter(
            piece__journal__code="BQ1", piece__exercice=exercice,
            piece__date_piece__year=annee, piece__date_piece__month=2,
            compte__numero="521",
        ).select_related("piece")

        lignes = [
            {
                "date_operation": m.piece.date_piece,
                "libelle": m.piece.libelle,
                "montant": m.debit - m.credit,  # signé : + encaissement / - décaissement
                "reference_banque": m.piece.reference,
            }
            for m in mouvements
        ]
        lignes += [
            {"date_operation": date(annee, 2, 26), "libelle": "Frais de tenue de compte",
             "montant": Decimal("-15000.00"), "reference_banque": "FRAIS-02"},
            {"date_operation": date(annee, 2, 27), "libelle": "Commission de virement",
             "montant": Decimal("-7500.00"), "reference_banque": "COM-02"},
        ]
        releve = creer_releve_depuis_lignes(
            compte, lignes,
            date_debut=date(annee, 2, 1), date_fin=date(annee, 2, 28),
            solde_initial=compte.solde_initial,
            solde_final=compte.solde_initial + sum(x["montant"] for x in lignes),
        )
        pointees = pointer_automatiquement(releve)
        total = LigneReleve.objects.filter(releve=releve).count()
        return f"1 compte, relevé de {total} lignes dont {pointees} pointées automatiquement"

    def _creer_declarations(self, exercice, user):
        from apps.fiscal.models import ConfigurationAIB, ConfigurationIS, ConfigurationTVA
        from apps.fiscal.services import creer_declaration_aib, creer_declaration_is, creer_declaration_tva

        resume = []
        config_tva = ConfigurationTVA.objects.filter(actif=True).first()
        if config_tva:
            for mois in (1, 2):
                creer_declaration_tva(config_tva, exercice.date_debut.year, mois, user)
            resume.append("2 déclarations TVA")

        config_is = ConfigurationIS.objects.filter(actif=True).first()
        if config_is:
            creer_declaration_is(config_is, exercice, user)
            resume.append("1 déclaration IS")

        config_aib = ConfigurationAIB.objects.filter(actif=True).first()
        if config_aib:
            creer_declaration_aib(config_aib, exercice.date_debut.year, 1, Decimal("5000000.00"), user)
            resume.append("1 déclaration AIB")
        return ", ".join(resume) or "aucune configuration fiscale"
