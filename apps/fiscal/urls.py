from django.urls import path

from . import views

app_name = "fiscal"

urlpatterns = [
    path("tva/", views.declaration_list, name="declaration_list"),
    path("tva/<int:pk>/liquider/", views.liquider, name="liquider"),
    path("tva/<int:pk>/bordereau/", views.bordereau, name="bordereau"),
    path("is/", views.is_list, name="is_list"),
    path("is/<int:pk>/", views.is_detail, name="is_detail"),
    path("is/<int:pk>/comptabiliser/", views.is_comptabiliser, name="is_comptabiliser"),
    path("is/<int:pk>/bordereau/", views.is_bordereau, name="is_bordereau"),
    path("aib/", views.aib_list, name="aib_list"),
    path("aib/<int:pk>/comptabiliser/", views.aib_comptabiliser, name="aib_comptabiliser"),
    path("aib/<int:pk>/bordereau/", views.aib_bordereau, name="aib_bordereau"),
]
