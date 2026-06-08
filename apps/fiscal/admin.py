from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import ConfigurationTVA, DeclarationTVA


@admin.register(ConfigurationTVA)
class ConfigurationTVAAdmin(ModelAdmin):
    list_display = ("libelle", "periodicite", "actif")
    filter_horizontal = ("comptes_collectee", "comptes_deductible")


@admin.register(DeclarationTVA)
class DeclarationTVAAdmin(ModelAdmin):
    list_display = ("annee", "periode_num", "tva_collectee", "tva_deductible", "tva_nette", "statut")
    list_filter = ("statut", "annee", "configuration")
