from django.urls import path

from . import views

app_name = "comptabilite"

urlpatterns = [
    path("pieces/", views.PieceListView.as_view(), name="piece_list"),
    path("pieces/nouvelle/", views.piece_create, name="piece_create"),
    path("pieces/<int:pk>/", views.PieceDetailView.as_view(), name="piece_detail"),
    path("pieces/<int:pk>/edit/", views.piece_update, name="piece_update"),
    path("pieces/<int:pk>/valider/", views.piece_valider_view, name="piece_valider"),
    path("pieces/<int:pk>/supprimer/", views.piece_supprimer_brouillard, name="piece_supprimer"),
    # Lettrage
    path("tiers/<int:tiers_id>/grand-livre/", views.grand_livre_tiers, name="grand_livre_tiers"),
    path("lettrage/", views.lettrer_view, name="lettrer"),
    path("delettrage/<int:tiers_id>/<str:code_lettre>/", views.delettrer_view, name="delettrer"),
    # Clôture
    path("cloture/", views.cloture_liste, name="cloture_liste"),
    path("cloture/<int:pk>/", views.cloture, name="cloture"),
    # HTMX
    path("htmx/comptes/", views.htmx_comptes_search, name="htmx_comptes"),
    path("htmx/tiers/", views.htmx_tiers_search, name="htmx_tiers"),
    path("htmx/pieces/nouvelle-ligne/", views.htmx_nouvelle_ligne, name="htmx_nouvelle_ligne"),
    path("htmx/pieces/totaux/", views.htmx_totaux, name="htmx_totaux"),
]
