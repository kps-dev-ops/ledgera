from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from django_tenants.models import DomainMixin, TenantMixin

REFERENTIEL_CHOICES = [
    ("SYSCOHADA", "SYSCOHADA 2017"),
    ("PCG_FR", "PCG France"),
    ("PCMN_BE", "PCMN Belgique"),
    ("PCT_TN", "PCT Tunisie"),
]

PAYS_CHOICES = [
    ("BJ", "Bénin"),
    ("CI", "Côte d'Ivoire"),
    ("SN", "Sénégal"),
    ("TG", "Togo"),
    ("CM", "Cameroun"),
    ("FR", "France"),
    ("BE", "Belgique"),
    ("TN", "Tunisie"),
]

DEVISE_CHOICES = [
    ("XOF", "Franc CFA BCEAO"),
    ("XAF", "Franc CFA BEAC"),
    ("EUR", "Euro"),
    ("TND", "Dinar Tunisien"),
    ("USD", "Dollar US"),
]

_schema_name_validator = RegexValidator(
    r"^[a-z][a-z0-9_]{0,61}$",
    "schema_name : lettres minuscules, chiffres et underscores uniquement (max 62 car.).",
)


class Societe(TenantMixin):
    """
    Entité juridique = tenant PostgreSQL.
    Chaque société a son propre schema isolé dans la base de données.
    Le schema_name est utilisé directement comme nom de schema PG — doit être un identifiant valide.
    """

    code = models.CharField(max_length=20, unique=True)
    raison_sociale = models.CharField(max_length=200)
    pays = models.CharField(max_length=5, choices=PAYS_CHOICES, db_index=True)
    devise = models.CharField(max_length=5, choices=DEVISE_CHOICES, default="XOF")
    referentiel = models.CharField(max_length=20, choices=REFERENTIEL_CHOICES, default="SYSCOHADA")
    plan_comptes_type = models.ForeignKey(
        "referentiels.PlanComptableType",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="societes",
    )
    ifu_siret = models.CharField(max_length=50, blank=True)
    # Mois de début de l'exercice comptable (1=janvier, 7=juillet pour exercices décalés)
    exercice_debut_mois = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(12)],
    )
    statut = models.CharField(
        max_length=20,
        choices=[("active", "Active"), ("suspendue", "Suspendue"), ("archivee", "Archivée")],
        default="active",
    )

    auto_create_schema = True

    class Meta:
        verbose_name = "Société"
        verbose_name_plural = "Sociétés"

    def clean(self):
        _schema_name_validator(self.schema_name)
        super().clean()

    def __str__(self):
        return f"{self.code} — {self.raison_sociale}"


class Domain(DomainMixin):
    """Domaine DNS associé à un tenant. Une société peut avoir plusieurs domaines."""

    def __str__(self):
        return self.domain
