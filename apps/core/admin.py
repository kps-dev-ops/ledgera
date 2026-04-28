from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import SocieteMembership, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("email", "statut", "is_2fa_enabled", "is_staff")
    list_filter = ("statut", "is_staff")
    search_fields = ("email", "first_name", "last_name")
    ordering = ("email",)
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Informations personnelles", {"fields": ("first_name", "last_name")}),
        ("Sécurité", {"fields": ("statut", "date_derniere_connexion_2fa")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "password1", "password2"),
        }),
    )


@admin.register(SocieteMembership)
class SocieteMembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "societe", "role", "actif")
    list_filter = ("role", "actif")
    search_fields = ("user__email",)
