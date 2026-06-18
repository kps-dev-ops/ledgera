from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import ConfigurationIS, ConfigurationTVA, DeclarationIS, DeclarationTVA, RetraitementFiscal


@admin.register(ConfigurationTVA)
class ConfigurationTVAAdmin(ModelAdmin):
    list_display = ("libelle", "periodicite", "actif")
    filter_horizontal = ("comptes_collectee", "comptes_deductible")


@admin.register(DeclarationTVA)
class DeclarationTVAAdmin(ModelAdmin):
    list_display = ("annee", "periode_num", "tva_collectee", "tva_deductible", "tva_nette", "statut")
    list_filter = ("statut", "annee", "configuration")


@admin.register(ConfigurationIS)
class ConfigurationISAdmin(ModelAdmin):
    list_display = ("libelle", "taux", "actif")


class RetraitementInline(admin.TabularInline):
    model = RetraitementFiscal
    extra = 0


@admin.register(DeclarationIS)
class DeclarationISAdmin(ModelAdmin):
    list_display = ("exercice", "resultat_comptable", "resultat_fiscal", "impot", "statut")
    list_filter = ("statut",)
    inlines = [RetraitementInline]
