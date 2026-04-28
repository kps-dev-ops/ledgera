from django.db import models

SENS_CHOICES = [
    ("debiteur", "Débiteur"),
    ("crediteur", "Créditeur"),
    ("mixte", "Mixte"),
]


class PlanComptableType(models.Model):
    """Plan de comptes type (SYSCOHADA, PCG France, etc.) — lecture seule en production."""

    code = models.CharField(max_length=30, unique=True)
    libelle = models.CharField(max_length=200)
    pays_applicable = models.CharField(max_length=50)
    version = models.CharField(max_length=20)
    date_effet = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = "Plan comptable type"
        verbose_name_plural = "Plans comptables types"
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} — {self.libelle}"


class CompteType(models.Model):
    """Compte dans un plan de comptes type. Sert de modèle à la création du tenant."""

    plan = models.ForeignKey(PlanComptableType, on_delete=models.CASCADE, related_name="comptes")
    numero = models.CharField(max_length=20)
    libelle = models.CharField(max_length=200)
    classe = models.PositiveSmallIntegerField()
    sens = models.CharField(max_length=10, choices=SENS_CHOICES)
    collectif_tiers = models.BooleanField(default=False)
    analytique_ok = models.BooleanField(default=False)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="enfants"
    )

    class Meta:
        verbose_name = "Compte type"
        verbose_name_plural = "Comptes types"
        unique_together = [("plan", "numero")]
        ordering = ["numero"]

    def __str__(self):
        return f"{self.numero} — {self.libelle}"
