from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, SocieteMembership


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("email", "statut", "is_2fa_enabled", "is_staff")
    list_filter = ("statut", "is_2fa_enabled", "is_staff")
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Sécurité", {"fields": ("statut", "is_2fa_enabled", "totp_secret", "date_derniere_connexion")}),
    )


@admin.register(SocieteMembership)
class SocieteMembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "societe", "role", "actif")
    list_filter = ("role", "actif")
