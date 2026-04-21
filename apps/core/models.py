from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Utilisateur Ledgera. Identifiant = email.
    La 2FA est gérée via django-otp (TOTPDevice) — pas de secret stocké ici.
    """

    STATUT_CHOICES = [
        ("actif", "Actif"),
        ("suspendu", "Suspendu"),
        ("verrouille", "Verrouillé"),
    ]

    # Rendre username optionnel (allauth crée les users par email, pas par username)
    username = models.CharField(max_length=150, blank=True, default="")
    email = models.EmailField(unique=True)
    # date_derniere_connexion_2fa track la dernière connexion avec 2FA validée
    # (distinct de AbstractUser.last_login qui track toute connexion)
    date_derniere_connexion_2fa = models.DateTimeField(null=True, blank=True)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default="actif")

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"

    def __str__(self):
        return self.email

    @property
    def is_2fa_enabled(self) -> bool:
        """Vérifie si l'utilisateur a au moins un appareil TOTP confirmé via django-otp."""
        return self.totpdevice_set.filter(confirmed=True).exists()


class SocieteMembership(models.Model):
    """
    Liaison utilisateur ↔ société.
    Un utilisateur ne peut avoir qu'un seul rôle actif par société.
    """

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
        # Un seul rôle par utilisateur par société
        unique_together = [("user", "societe")]

    def __str__(self):
        return f"{self.user.email} — {self.role} @ {self.societe}"
