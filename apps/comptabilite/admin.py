from django.contrib import admin

from .models import CompteComptable, Exercice, Journal, LigneEcriture, Periode, PieceComptable


@admin.register(Exercice)
class ExerciceAdmin(admin.ModelAdmin):
    list_display = ("code", "date_debut", "date_fin", "statut")
    list_filter = ("statut",)


@admin.register(Periode)
class PeriodeAdmin(admin.ModelAdmin):
    list_display = ("exercice", "mois", "statut")
    list_filter = ("statut", "exercice")


@admin.register(CompteComptable)
class CompteComptableAdmin(admin.ModelAdmin):
    list_display = ("numero", "libelle", "classe", "sens", "collectif_tiers", "actif")
    list_filter = ("classe", "sens", "collectif_tiers", "actif")
    search_fields = ("numero", "libelle")


@admin.register(Journal)
class JournalAdmin(admin.ModelAdmin):
    list_display = ("code", "libelle", "type_journal", "compte_contrepartie", "actif")
    list_filter = ("type_journal", "actif")


class LigneEcritureInline(admin.TabularInline):
    model = LigneEcriture
    extra = 0
    fields = ("numero_ligne", "compte", "tiers", "libelle", "debit", "credit", "lettre_lettrage")


@admin.register(PieceComptable)
class PieceComptableAdmin(admin.ModelAdmin):
    list_display = ("__str__", "journal", "exercice", "date_piece", "statut", "total_debit", "total_credit")
    list_filter = ("statut", "journal", "exercice")
    search_fields = ("libelle", "reference", "numero")
    readonly_fields = ("date_saisie", "date_validation", "validee_par", "total_debit", "total_credit")
    inlines = [LigneEcritureInline]
