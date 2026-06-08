from decimal import Decimal

from django.db import models
from django.db.models import CheckConstraint, F, Index, Q


class CompteBancaire(models.Model):
    libelle = models.CharField(max_length=200)
    compte_comptable = models.ForeignKey(
        "comptabilite.CompteComptable", on_delete=models.PROTECT, related_name="comptes_bancaires"
    )
    journal = models.ForeignKey(
        "comptabilite.Journal", on_delete=models.PROTECT, related_name="comptes_bancaires"
    )
    banque_nom = models.CharField(max_length=100, blank=True, default="")
    iban = models.CharField(max_length=34, blank=True, default="")
    bic = models.CharField(max_length=11, blank=True, default="")
    devise = models.CharField(max_length=3, default="XOF")
    solde_initial = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    actif = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Compte bancaire"
        verbose_name_plural = "Comptes bancaires"
        ordering = ["libelle"]

    def __str__(self):
        return f"{self.libelle} ({self.compte_comptable.numero})"


class ReleveBancaire(models.Model):
    STATUT_CHOICES = [
        ("EN_COURS", "En cours"),
        ("RAPPROCHE", "Rapproché"),
        ("CLOS", "Clos"),
    ]
    compte_bancaire = models.ForeignKey(
        CompteBancaire, on_delete=models.PROTECT, related_name="releves"
    )
    date_debut = models.DateField()
    date_fin = models.DateField()
    solde_initial = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    solde_final = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    statut = models.CharField(max_length=10, choices=STATUT_CHOICES, default="EN_COURS")
    fichier_source = models.FileField(upload_to="releves/", null=True, blank=True)
    date_import = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Relevé bancaire"
        verbose_name_plural = "Relevés bancaires"
        ordering = ["-date_debut"]
        constraints = [
            CheckConstraint(condition=Q(date_fin__gte=F("date_debut")), name="releve_dates_coherentes"),
        ]

    def __str__(self):
        return f"Relevé {self.compte_bancaire.libelle} {self.date_debut}→{self.date_fin}"


class LigneReleve(models.Model):
    STATUT_CHOICES = [
        ("NON_POINTEE", "Non pointée"),
        ("POINTEE_AUTO", "Pointée (auto)"),
        ("POINTEE_MANUEL", "Pointée (manuel)"),
    ]
    releve = models.ForeignKey(ReleveBancaire, on_delete=models.CASCADE, related_name="lignes")
    date_operation = models.DateField()
    libelle = models.CharField(max_length=200)
    montant = models.DecimalField(max_digits=15, decimal_places=2, help_text="Signé : + encaissement / - décaissement")
    reference_banque = models.CharField(max_length=50, blank=True, default="")
    ligne_ecriture_pointee = models.ForeignKey(
        "comptabilite.LigneEcriture", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="lignes_releve",
    )
    statut = models.CharField(max_length=15, choices=STATUT_CHOICES, default="NON_POINTEE")

    class Meta:
        verbose_name = "Ligne de relevé"
        verbose_name_plural = "Lignes de relevé"
        ordering = ["releve", "date_operation"]
        constraints = [
            CheckConstraint(condition=~Q(montant=0), name="ligne_releve_montant_non_nul"),
        ]
        indexes = [Index(fields=["releve", "statut"])]

    def __str__(self):
        return f"{self.date_operation} {self.libelle} {self.montant}"
