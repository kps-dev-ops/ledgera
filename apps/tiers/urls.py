from django.urls import path

from . import views

app_name = "tiers"

urlpatterns = [
    path("", views.TiersListView.as_view(), name="tiers_list"),
    path("nouveau/", views.TiersCreateView.as_view(), name="tiers_create"),
    path("<int:pk>/", views.TiersDetailView.as_view(), name="tiers_detail"),
    path("<int:pk>/edit/", views.TiersUpdateView.as_view(), name="tiers_update"),
]
