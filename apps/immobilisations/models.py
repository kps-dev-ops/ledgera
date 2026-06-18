from decimal import Decimal

from django.db import models
from django.db.models import CheckConstraint, F, Index, Q, UniqueConstraint


class CategorieImmobilisation(models.Model):
    MODE_CHOICES = [("LINEAIRE", "Linéaire"), ("DEGRESSIF", "Dégressif")]

    code = models.CharField(max_length=20, unique=True)
    libelle = models.CharField(max_length=200)
    compte_immo = models.ForeignKey(
        "comptabilite.CompteComptable", on_delete=models.PROTECT, related_name="categories_immo"
    )
    compte_amortissement = models.ForeignKey(
        "comptabilite.CompteComptable", on_delete=models.PROTECT, related_name="categories_amort"
    )
    compte_dotation = models.ForeignKey(
        "comptabilite.CompteComptable", on_delete=models.PROTECT, related_name="categories_dotation"
    )
    duree_defaut = models.PositiveSmallIntegerField()
    mode_defaut = models.CharField(max_length=10, choices=MODE_CHOICES, default="LINEAIRE")
    actif = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Catégorie d'immobilisation"
        verbose_name_plural = "Catégories d'immobilisation"
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} — {self.libelle}"


class Immobilisation(models.Model):
    MODE_CHOICES = [("LINEAIRE", "Linéaire"), ("DEGRESSIF", "Dégressif")]
    STATUT_CHOICES = [
        ("EN_COURS", "En cours"),
        ("EN_SERVICE", "En service"),
        ("CEDEE", "Cédée"),
        ("REBUT", "Mise au rebut"),
    ]

    code = models.CharField(max_length=12, unique=True, db_index=True)
    designation = models.CharField(max_length=200)
    categorie = models.ForeignKey(
        CategorieImmobilisation, on_delete=models.PROTECT, related_name="immobilisations"
    )
    date_acquisition = models.DateField()
    date_mise_service = models.DateField()
    cout_acquisition = models.DecimalField(max_digits=15, decimal_places=2)
    valeur_residuelle = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    duree = models.PositiveSmallIntegerField(help_text="Durée d'amortissement en années")
    mode_amortissement = models.CharField(max_length=10, choices=MODE_CHOICES, default="LINEAIRE")
    compte_immo = models.ForeignKey(
        "comptabilite.CompteComptable", on_delete=models.PROTECT, related_name="immos"
    )
    compte_amortissement = models.ForeignKey(
        "comptabilite.CompteComptable", on_delete=models.PROTECT, related_name="immos_amort"
    )
    compte_dotation = models.ForeignKey(
        "comptabilite.CompteComptable", on_delete=models.PROTECT, related_name="immos_dotation"
    )
    statut = models.CharField(max_length=12, choices=STATUT_CHOICES, default="EN_COURS")
    date_cession = models.DateField(null=True, blank=True)
    prix_cession = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    piece_cession = models.ForeignKey(
        "comptabilite.PieceComptable", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="cessions_immo",
    )
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Immobilisation"
        verbose_name_plural = "Immobilisations"
        ordering = ["code"]
        indexes = [Index(fields=["statut"])]
        constraints = [
            CheckConstraint(condition=Q(cout_acquisition__gt=0), name="immo_cout_positif"),
            CheckConstraint(condition=Q(duree__gte=1), name="immo_duree_min"),
            CheckConstraint(
                condition=Q(valeur_residuelle__gte=0) & Q(valeur_residuelle__lt=F("cout_acquisition")),
                name="immo_valeur_residuelle_coherente",
            ),
        ]

    def __str__(self):
        return f"{self.code} — {self.designation}"


class Dotation(models.Model):
    STATUT_CHOICES = [("PREVUE", "Prévue"), ("COMPTABILISEE", "Comptabilisée")]

    immobilisation = models.ForeignKey(
        Immobilisation, on_delete=models.CASCADE, related_name="dotations"
    )
    annee = models.PositiveSmallIntegerField()
    mois = models.PositiveSmallIntegerField()
    montant = models.DecimalField(max_digits=15, decimal_places=2)
    cumul = models.DecimalField(max_digits=15, decimal_places=2)
    vnc = models.DecimalField(max_digits=15, decimal_places=2)
    statut = models.CharField(max_length=15, choices=STATUT_CHOICES, default="PREVUE")
    piece_generee = models.ForeignKey(
        "comptabilite.PieceComptable", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="dotations",
    )

    class Meta:
        verbose_name = "Dotation aux amortissements"
        verbose_name_plural = "Dotations aux amortissements"
        ordering = ["immobilisation", "annee", "mois"]
        constraints = [
            UniqueConstraint(fields=["immobilisation", "annee", "mois"], name="dotation_unique_periode"),
            CheckConstraint(condition=Q(mois__gte=1) & Q(mois__lte=12), name="dotation_mois_valide"),
            CheckConstraint(condition=Q(montant__gte=0), name="dotation_montant_positif"),
        ]
        indexes = [Index(fields=["annee", "mois", "statut"])]

    def __str__(self):
        return f"{self.immobilisation.code} {self.annee}-{self.mois:02d} : {self.montant}"


class ConfigurationCessionImmo(models.Model):
    compte_valeur_comptable = models.ForeignKey(
        "comptabilite.CompteComptable", on_delete=models.PROTECT, related_name="config_cession_vc"
    )
    compte_produit = models.ForeignKey(
        "comptabilite.CompteComptable", on_delete=models.PROTECT, related_name="config_cession_produit"
    )
    compte_creance = models.ForeignKey(
        "comptabilite.CompteComptable", on_delete=models.PROTECT, related_name="config_cession_creance"
    )
    actif = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Configuration cession immobilisation"
        verbose_name_plural = "Configurations cession immobilisation"

    def __str__(self):
        return (
            f"Cession : VC {self.compte_valeur_comptable.numero}"
            f" / produit {self.compte_produit.numero}"
            f" / créance {self.compte_creance.numero}"
        )
