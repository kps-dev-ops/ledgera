from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    STATUT_CHOICES = [
        ("actif", "Actif"),
        ("suspendu", "Suspendu"),
        ("verrouille", "Verrouillé"),
    ]

    email = models.EmailField(unique=True)
    totp_secret = models.CharField(max_length=64, blank=True)
    is_2fa_enabled = models.BooleanField(default=False)
    date_derniere_connexion = models.DateTimeField(null=True, blank=True)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default="actif")

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    class Meta:
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"

    def __str__(self):
        return self.email


class SocieteMembership(models.Model):
    ROLE_CHOICES = [
        ("admin", "Administrateur"),
        ("comptable_senior", "Comptable Senior"),
        ("comptable_junior", "Comptable Junior"),
        ("daf_lecture", "DAF Lecture"),
        ("auditeur", "Auditeur"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="memberships")
    societe = models.ForeignKey(
        "tenants.Societe", on_delete=models.CASCADE, related_name="memberships"
    )
    role = models.CharField(max_length=30, choices=ROLE_CHOICES)
    actif = models.BooleanField(default=True)
    date_debut = models.DateField(auto_now_add=True)
    date_fin = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = "Appartenance à une société"
        verbose_name_plural = "Appartenances"
        unique_together = [("user", "societe", "role")]

    def __str__(self):
        return f"{self.user.email} — {self.role} @ {self.societe_id}"
