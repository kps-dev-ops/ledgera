from django.contrib import admin

from .models import CompteType, PlanComptableType


@admin.register(PlanComptableType)
class PlanComptableTypeAdmin(admin.ModelAdmin):
    list_display = ("code", "libelle", "pays_applicable", "version")
    search_fields = ("code", "libelle")


@admin.register(CompteType)
class CompteTypeAdmin(admin.ModelAdmin):
    list_display = ("numero", "libelle", "plan", "classe", "sens", "collectif_tiers")
    list_filter = ("plan", "classe", "sens", "collectif_tiers")
    search_fields = ("numero", "libelle")
    raw_id_fields = ("parent",)
