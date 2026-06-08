from django.urls import path

from . import views

app_name = "immobilisations"

urlpatterns = [
    path("", views.ImmobilisationListView.as_view(), name="immo_list"),
    path("nouvelle/", views.ImmobilisationCreateView.as_view(), name="immo_create"),
    path("<int:pk>/", views.ImmobilisationDetailView.as_view(), name="immo_detail"),
    path("<int:pk>/edit/", views.ImmobilisationUpdateView.as_view(), name="immo_update"),
    path("<int:pk>/ceder/", views.ceder, name="immo_ceder"),
    path("htmx/comptes-categorie/", views.comptes_categorie, name="comptes_categorie"),
    path("comptabiliser/", views.comptabiliser, name="comptabiliser"),
]
