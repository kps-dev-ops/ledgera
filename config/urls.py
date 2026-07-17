from django.conf import settings
from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.urls import include, path
from django.views.generic import TemplateView

from apps.core import views as core_views

urlpatterns = [
    path("", login_required(TemplateView.as_view(template_name="dashboard.html")), name="dashboard"),
    path("societe/<int:pk>/activer/", core_views.activer_societe, name="activer_societe"),
    path("aucune-societe/", core_views.aucune_societe, name="aucune_societe"),
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("compta/", include("apps.comptabilite.urls")),
    path("compta/immos/", include("apps.immobilisations.urls")),
    path("compta/banque/", include("apps.banque.urls")),
    path("compta/fiscal/", include("apps.fiscal.urls")),
    path("tiers/", include("apps.tiers.urls")),
    path("etats/", include("apps.etats.urls")),
    path("io/", include("apps.imports_exports.urls")),
]

if settings.DEBUG:
    urlpatterns += [path("__reload__/", include("django_browser_reload.urls"))]
