from django.urls import path

from . import views

app_name = "fiscal"

urlpatterns = [
    path("tva/", views.declaration_list, name="declaration_list"),
    path("tva/<int:pk>/liquider/", views.liquider, name="liquider"),
    path("tva/<int:pk>/bordereau/", views.bordereau, name="bordereau"),
]
