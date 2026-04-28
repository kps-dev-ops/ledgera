from django.urls import path

from . import views

app_name = "imports_exports"

urlpatterns = [
    path("exports/", views.export_list, name="export_list"),
    path("exports/<str:type_export>/lancer/", views.export_create, name="export_create"),
    path("exports/<int:pk>/", views.export_detail, name="export_detail"),
    path("exports/<int:pk>/status/", views.export_status, name="export_status"),
    path("exports/<int:pk>/download/", views.export_download, name="export_download"),
    # Imports
    path("imports/", views.import_list, name="import_list"),
    path("imports/nouveau/", views.import_create, name="import_create"),
    path("imports/<int:pk>/", views.import_detail, name="import_detail"),
    path("imports/<int:pk>/status/", views.import_status, name="import_status"),
]
