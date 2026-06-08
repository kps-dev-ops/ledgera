from django.urls import path

from . import views

app_name = "banque"

urlpatterns = [
    path("", views.CompteBancaireListView.as_view(), name="compte_list"),
    path("comptes/nouveau/", views.CompteBancaireCreateView.as_view(), name="compte_create"),
    path("releves/importer/", views.importer_releve, name="releve_import"),
    path("releves/<int:pk>/", views.rapprochement, name="rapprochement"),
    path("releves/<int:pk>/pointer-auto/", views.pointer_auto, name="pointer_auto"),
    path("lignes/<int:ligne_pk>/pointer/", views.pointer_manuel, name="pointer_manuel"),
    path("lignes/<int:ligne_pk>/depointer/", views.depointer_ligne, name="depointer"),
]
