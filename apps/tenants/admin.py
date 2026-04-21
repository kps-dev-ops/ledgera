from django.contrib import admin
from .models import Societe, Domain


@admin.register(Societe)
class SocieteAdmin(admin.ModelAdmin):
    list_display = ("code", "raison_sociale", "pays", "devise", "referentiel", "statut")
    list_filter = ("pays", "referentiel", "statut")
    search_fields = ("code", "raison_sociale", "ifu_siret")
    readonly_fields = ("schema_name",)


@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    list_display = ("domain", "tenant", "is_primary")
    list_filter = ("is_primary",)
    search_fields = ("domain",)
