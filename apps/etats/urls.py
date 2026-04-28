from django.urls import path

from . import views

app_name = "etats"

urlpatterns = [
    path("balance/", views.balance_view, name="balance"),
    path("balance-auxiliaire/", views.balance_auxiliaire_view, name="balance_auxiliaire"),
    path("grand-livre/", views.grand_livre_view, name="grand_livre"),
    path("grand-livre/<str:numero>/", views.grand_livre_compte_view, name="grand_livre_compte"),
    path("journal/", views.journal_view, name="journal"),
    path("bilan/", views.bilan_view, name="bilan"),
    path("compte-resultat/", views.compte_resultat_view, name="compte_resultat"),
]
