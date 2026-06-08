from decimal import Decimal

from django.db import models
from django.db.models import UniqueConstraint


class ConfigurationTVA(models.Model):
    PERIODICITE_CHOICES = [("MENSUELLE", "Mensuelle"), ("TRIMESTRIELLE", "Trimestrielle")]

    libelle = models.CharField(max_length=200)
    periodicite = models.CharField(max_length=15, choices=PERIODICITE_CHOICES, default="MENSUELLE")
    comptes_collectee = models.ManyToManyField(
        "comptabilite.CompteComptable", related_name="config_tva_collectee"
    )
    comptes_deductible = models.ManyToManyField(
        "comptabilite.CompteComptable", related_name="config_tva_deductible"
    )
    compte_tva_due = models.ForeignKey(
        "comptabilite.CompteComptable", on_delete=models.PROTECT, related_name="config_tva_due"
    )
    compte_credit_tva = models.ForeignKey(
        "comptabilite.CompteComptable", on_delete=models.PROTECT, related_name="config_tva_credit"
    )
    journal = models.ForeignKey("comptabilite.Journal", on_delete=models.PROTECT, related_name="config_tva")
    actif = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Configuration TVA"
        verbose_name_plural = "Configurations TVA"
        ordering = ["libelle"]

    def __str__(self):
        return self.libelle


class DeclarationTVA(models.Model):
    STATUT_CHOICES = [("BROUILLON", "Brouillon"), ("VALIDEE", "Validée")]

    configuration = models.ForeignKey(ConfigurationTVA, on_delete=models.PROTECT, related_name="declarations")
    annee = models.PositiveSmallIntegerField()
    periode_num = models.PositiveSmallIntegerField(help_text="Mois (1-12) ou trimestre (1-4)")
    date_debut = models.DateField()
    date_fin = models.DateField()
    tva_collectee = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    tva_deductible = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    tva_nette = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    statut = models.CharField(max_length=10, choices=STATUT_CHOICES, default="BROUILLON")
    piece_liquidation = models.ForeignKey(
        "comptabilite.PieceComptable", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="declarations_tva",
    )
    bordereau = models.FileField(upload_to="bordereaux_tva/", null=True, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Déclaration TVA"
        verbose_name_plural = "Déclarations TVA"
        ordering = ["-annee", "-periode_num"]
        constraints = [
            UniqueConstraint(fields=["configuration", "annee", "periode_num"], name="declaration_tva_unique_periode"),
        ]

    def __str__(self):
        return f"TVA {self.periode_num:02d}/{self.annee} — net {self.tva_nette}"
