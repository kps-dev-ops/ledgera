from django.conf import settings
from django.db import models


class ImportJob(models.Model):
    STATUT_CHOICES = [
        ("EN_ATTENTE", "En attente"),
        ("EN_COURS", "En cours"),
        ("TERMINE", "Terminé"),
        ("ERREUR", "Erreur"),
    ]
    MODELE_CHOICES = [
        ("ACHATS", "Journal Achats"),
        ("VENTES", "Journal Ventes"),
        ("OD", "Opérations diverses"),
    ]

    fichier = models.FileField(upload_to="imports/")
    modele = models.CharField(max_length=20, choices=MODELE_CHOICES)
    journal_code = models.CharField(max_length=10)
    exercice_code = models.CharField(max_length=20)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default="EN_ATTENTE")
    rapport = models.JSONField(default=dict, blank=True)
    nb_lignes_traitees = models.PositiveIntegerField(default=0)
    nb_pieces_creees = models.PositiveIntegerField(default=0)
    cree_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_fin = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-date_creation"]
        verbose_name = "Job d'import"
        verbose_name_plural = "Jobs d'import"

    def __str__(self):
        return f"Import #{self.pk} {self.modele} ({self.statut})"


class ExportJob(models.Model):
    STATUT_CHOICES = [
        ("EN_ATTENTE", "En attente"),
        ("EN_COURS", "En cours"),
        ("TERMINE", "Terminé"),
        ("ERREUR", "Erreur"),
    ]
    TYPE_CHOICES = [
        ("FEC", "FEC (texte BOI)"),
        ("BALANCE_XLSX", "Balance Excel"),
        ("GL_XLSX", "Grand livre Excel"),
        ("JOURNAL_XLSX", "Journal Excel"),
        ("BALANCE_PDF", "Balance PDF"),
        ("BILAN_PDF", "Bilan PDF"),
        ("CR_PDF", "Compte de résultat PDF"),
    ]

    type_export = models.CharField(max_length=30, choices=TYPE_CHOICES)
    fichier = models.FileField(upload_to="exports/", null=True, blank=True)
    parametres = models.JSONField(default=dict, blank=True)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default="EN_ATTENTE")
    erreur = models.TextField(blank=True, default="")
    cree_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_fin = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-date_creation"]
        verbose_name = "Job d'export"
        verbose_name_plural = "Jobs d'export"

    def __str__(self):
        return f"Export #{self.pk} {self.type_export} ({self.statut})"
