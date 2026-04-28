from django.db import models


class Tiers(models.Model):
    TYPE_CHOICES = [
        ("CLIENT", "Client"),
        ("FOURNISSEUR", "Fournisseur"),
        ("DIVERS", "Divers"),
    ]
    MODE_REGLEMENT_CHOICES = [
        ("VIREMENT", "Virement"),
        ("CHEQUE", "Chèque"),
        ("ESPECES", "Espèces"),
        ("PRELEVEMENT", "Prélèvement"),
    ]

    type_tiers = models.CharField(max_length=20, choices=TYPE_CHOICES)
    code_auxiliaire = models.CharField(max_length=10, unique=True, db_index=True)
    compte_collectif = models.ForeignKey(
        "comptabilite.CompteComptable",
        on_delete=models.PROTECT,
        related_name="tiers",
        limit_choices_to={"collectif_tiers": True},
    )
    raison_sociale = models.CharField(max_length=200)
    forme_juridique = models.CharField(max_length=50, blank=True, default="")
    identifiant_fiscal = models.CharField(max_length=50, blank=True, default="")
    adresse = models.CharField(max_length=200, blank=True, default="")
    cp = models.CharField(max_length=20, blank=True, default="")
    ville = models.CharField(max_length=100, blank=True, default="")
    pays = models.CharField(max_length=2, default="BJ")
    contacts = models.JSONField(default=list, blank=True)
    iban = models.CharField(max_length=34, blank=True, default="")
    bic = models.CharField(max_length=11, blank=True, default="")
    delai_reglement_jours = models.PositiveIntegerField(default=30)
    mode_reglement = models.CharField(max_length=20, choices=MODE_REGLEMENT_CHOICES, default="VIREMENT")
    actif = models.BooleanField(default=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Tiers"
        verbose_name_plural = "Tiers"
        ordering = ["raison_sociale"]
        indexes = [
            models.Index(fields=["raison_sociale"]),
            models.Index(fields=["type_tiers"]),
        ]

    def __str__(self):
        return f"{self.code_auxiliaire} — {self.raison_sociale}"
