from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import CompteBancaire, LigneReleve, ReleveBancaire


@admin.register(CompteBancaire)
class CompteBancaireAdmin(ModelAdmin):
    list_display = ("libelle", "banque_nom", "compte_comptable", "devise", "actif")
    search_fields = ("libelle", "banque_nom", "iban")


@admin.register(ReleveBancaire)
class ReleveBancaireAdmin(ModelAdmin):
    list_display = ("compte_bancaire", "date_debut", "date_fin", "statut")
    list_filter = ("statut", "compte_bancaire")


@admin.register(LigneReleve)
class LigneReleveAdmin(ModelAdmin):
    list_display = ("date_operation", "libelle", "montant", "statut")
    list_filter = ("statut",)
    search_fields = ("libelle", "reference_banque")
