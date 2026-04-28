from django.contrib import admin

from .models import Tiers


@admin.register(Tiers)
class TiersAdmin(admin.ModelAdmin):
    list_display = ("code_auxiliaire", "raison_sociale", "type_tiers", "compte_collectif", "actif")
    list_filter = ("type_tiers", "actif", "pays", "mode_reglement")
    search_fields = ("code_auxiliaire", "raison_sociale", "identifiant_fiscal")
    readonly_fields = ("code_auxiliaire", "date_creation")
    fieldsets = (
        ("Identification", {"fields": ("type_tiers", "code_auxiliaire", "compte_collectif", "raison_sociale",
                                       "forme_juridique", "identifiant_fiscal")}),
        ("Adresse", {"fields": ("adresse", "cp", "ville", "pays")}),
        ("Règlement", {"fields": ("iban", "bic", "delai_reglement_jours", "mode_reglement")}),
        ("Contacts", {"fields": ("contacts",)}),
        ("État", {"fields": ("actif", "date_creation")}),
    )
