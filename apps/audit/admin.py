from django.contrib import admin
from .models import JournalAudit


@admin.register(JournalAudit)
class JournalAuditAdmin(admin.ModelAdmin):
    list_display = ("horodatage", "action", "table_cible", "enregistrement_id", "utilisateur_email")
    list_filter = ("action", "table_cible")
    search_fields = ("utilisateur_email", "table_cible")
    readonly_fields = ("horodatage", "utilisateur_id", "utilisateur_email", "action",
                       "table_cible", "enregistrement_id", "valeurs_avant", "valeurs_apres",
                       "ip_adresse", "user_agent")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
