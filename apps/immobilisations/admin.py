from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import CategorieImmobilisation, Dotation, Immobilisation


@admin.register(CategorieImmobilisation)
class CategorieImmobilisationAdmin(ModelAdmin):
    list_display = ("code", "libelle", "duree_defaut", "mode_defaut", "actif")
    search_fields = ("code", "libelle")


@admin.register(Immobilisation)
class ImmobilisationAdmin(ModelAdmin):
    list_display = ("code", "designation", "categorie", "cout_acquisition", "statut")
    list_filter = ("statut", "categorie", "mode_amortissement")
    search_fields = ("code", "designation")
    readonly_fields = ("code", "date_creation")


@admin.register(Dotation)
class DotationAdmin(ModelAdmin):
    list_display = ("immobilisation", "annee", "mois", "montant", "statut")
    list_filter = ("statut", "annee")
    search_fields = ("immobilisation__code",)
