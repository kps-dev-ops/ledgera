from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import CheckConstraint, F, Index, Q, UniqueConstraint


class Exercice(models.Model):
    STATUT_CHOICES = [
        ("OUVERT", "Ouvert"),
        ("EN_COURS_CLOTURE", "En cours de clôture"),
        ("CLOTURE", "Clôturé"),
    ]
    code = models.CharField(max_length=20, unique=True)
    date_debut = models.DateField()
    date_fin = models.DateField()
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default="OUVERT")
    exercice_precedent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="suivants"
    )
    date_cloture = models.DateTimeField(null=True, blank=True)
    cloture_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="exercices_clotures"
    )

    class Meta:
        verbose_name = "Exercice"
        verbose_name_plural = "Exercices"
        ordering = ["-date_debut"]
        constraints = [
            CheckConstraint(condition=Q(date_fin__gt=F("date_debut")), name="exercice_dates_coherentes"),
        ]

    def __str__(self):
        return f"Exercice {self.code} ({self.date_debut} → {self.date_fin})"


class Periode(models.Model):
    STATUT_CHOICES = [
        ("OUVERTE", "Ouverte"),
        ("VERROUILLEE", "Verrouillée"),
        ("CLOTUREE", "Clôturée"),
    ]
    exercice = models.ForeignKey(Exercice, on_delete=models.CASCADE, related_name="periodes")
    mois = models.PositiveSmallIntegerField()
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default="OUVERTE")

    class Meta:
        verbose_name = "Période"
        verbose_name_plural = "Périodes"
        ordering = ["exercice", "mois"]
        constraints = [
            UniqueConstraint(fields=["exercice", "mois"], name="periode_unique_par_exercice"),
            CheckConstraint(condition=Q(mois__gte=1) & Q(mois__lte=12), name="periode_mois_valide"),
        ]

    def __str__(self):
        return f"{self.exercice.code} - {self.mois:02d}"


class CompteComptable(models.Model):
    SENS_CHOICES = [
        ("DEBITEUR", "Débiteur"),
        ("CREDITEUR", "Créditeur"),
        ("MIXTE", "Mixte"),
    ]
    numero = models.CharField(max_length=20, unique=True, db_index=True)
    libelle = models.CharField(max_length=200)
    classe = models.PositiveSmallIntegerField()
    sens = models.CharField(max_length=10, choices=SENS_CHOICES, default="MIXTE")
    collectif_tiers = models.BooleanField(default=False)
    analytique_ok = models.BooleanField(default=False)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="enfants"
    )
    actif = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Compte comptable"
        verbose_name_plural = "Plan de comptes"
        ordering = ["numero"]
        indexes = [Index(fields=["classe"]), Index(fields=["collectif_tiers"])]

    def __str__(self):
        return f"{self.numero} — {self.libelle}"


class Journal(models.Model):
    TYPE_CHOICES = [
        ("ACHATS", "Achats"),
        ("VENTES", "Ventes"),
        ("BANQUE", "Banque"),
        ("CAISSE", "Caisse"),
        ("OD", "Opérations diverses"),
        ("AN", "À-nouveaux"),
        ("PAIE", "Paie"),
    ]
    code = models.CharField(max_length=10, unique=True)
    libelle = models.CharField(max_length=100)
    type_journal = models.CharField(max_length=10, choices=TYPE_CHOICES)
    compte_contrepartie = models.ForeignKey(
        CompteComptable,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="journaux",
        help_text="Obligatoire pour BANQUE / CAISSE",
    )
    actif = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Journal"
        verbose_name_plural = "Journaux"
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} — {self.libelle}"


class PieceComptable(models.Model):
    STATUT_CHOICES = [
        ("BROUILLARD", "Brouillard"),
        ("VALIDEE", "Validée"),
        ("EXTOURNEE", "Extournée"),
    ]
    journal = models.ForeignKey(Journal, on_delete=models.PROTECT, related_name="pieces")
    exercice = models.ForeignKey(Exercice, on_delete=models.PROTECT, related_name="pieces")
    numero = models.PositiveIntegerField(null=True, blank=True)  # Attribué à la validation (R4)
    date_piece = models.DateField()
    date_saisie = models.DateTimeField(auto_now_add=True)
    reference = models.CharField(max_length=50, blank=True, default="")
    libelle = models.CharField(max_length=200)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default="BROUILLARD")
    auteur = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="pieces_creees"
    )
    date_validation = models.DateTimeField(null=True, blank=True)
    validee_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="pieces_validees",
    )
    piece_extournee = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="extournes"
    )
    total_debit = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    total_credit = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        verbose_name = "Pièce comptable"
        verbose_name_plural = "Pièces comptables"
        ordering = ["-date_piece", "-date_saisie"]
        constraints = [
            CheckConstraint(
                check=Q(statut="BROUILLARD") | Q(total_debit=F("total_credit")),
                name="piece_equilibree_si_validee",
            ),
            UniqueConstraint(
                fields=["journal", "exercice", "numero"],
                condition=Q(numero__isnull=False),
                name="piece_numero_unique_par_journal_exercice",
            ),
        ]
        indexes = [
            Index(fields=["exercice", "statut"]),
            Index(fields=["date_piece"]),
        ]

    def __str__(self):
        ref = f"#{self.numero}" if self.numero else "(brouillard)"
        return f"{self.journal.code} {ref} — {self.libelle}"


class LigneEcriture(models.Model):
    piece = models.ForeignKey(PieceComptable, on_delete=models.CASCADE, related_name="lignes")
    numero_ligne = models.PositiveSmallIntegerField()
    compte = models.ForeignKey(CompteComptable, on_delete=models.PROTECT, related_name="lignes")
    tiers = models.ForeignKey(
        "tiers.Tiers", null=True, blank=True, on_delete=models.PROTECT, related_name="lignes"
    )
    libelle = models.CharField(max_length=200, blank=True, default="")
    debit = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    credit = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    date_echeance = models.DateField(null=True, blank=True)
    date_operation = models.DateField(null=True, blank=True)
    pointee = models.BooleanField(default=False)
    lettre_lettrage = models.CharField(max_length=3, blank=True, default="", db_index=True)

    class Meta:
        verbose_name = "Ligne d'écriture"
        verbose_name_plural = "Lignes d'écriture"
        ordering = ["piece", "numero_ligne"]
        constraints = [
            CheckConstraint(
                check=(Q(debit__gt=0) & Q(credit=0)) | (Q(debit=0) & Q(credit__gt=0)),
                name="ligne_debit_xor_credit",
            ),
            UniqueConstraint(fields=["piece", "numero_ligne"], name="ligne_numero_unique_dans_piece"),
        ]
        indexes = [
            Index(fields=["compte", "date_operation"]),
        ]

    def __str__(self):
        montant = self.debit if self.debit else self.credit
        sens = "D" if self.debit else "C"
        return f"L{self.numero_ligne} {self.compte.numero} {sens}={montant}"
