from django.db import models


class JournalAudit(models.Model):
    ACTION_CHOICES = [
        ("INSERT", "Insertion"),
        ("UPDATE", "Modification"),
        ("DELETE", "Suppression"),
        ("VALIDATE", "Validation"),
        ("CLOSE", "Clôture"),
        ("TEST", "Test"),
    ]

    horodatage = models.DateTimeField(auto_now_add=True, db_index=True)
    utilisateur_id = models.IntegerField()
    utilisateur_email = models.EmailField()
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    table_cible = models.CharField(max_length=100)
    enregistrement_id = models.BigIntegerField()
    valeurs_avant = models.JSONField(null=True, blank=True)
    valeurs_apres = models.JSONField(null=True, blank=True)
    ip_adresse = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default="")

    class Meta:
        verbose_name = "Entrée d'audit"
        verbose_name_plural = "Journal d'audit"
        ordering = ["-horodatage"]

    def __str__(self):
        return f"{self.horodatage} — {self.action} sur {self.table_cible}#{self.enregistrement_id}"
