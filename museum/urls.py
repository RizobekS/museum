# apps/museum/urls.py
from django.urls import path
from .views import (
    ExhibitListView,
    ExhibitDetailByCodesView,
    ExhibitCi360Manifest,
)

app_name = "museum"

urlpatterns = [
    # Список экспонатов
    path("", ExhibitListView.as_view(), name="exhibit_list"),

    path("<slug:museum_code>/<str:exhibit_code>/", ExhibitDetailByCodesView.as_view(),
         name="exhibit_detail_qr"),

    # JSON манифест для 360
    path("exhibits/api/<slug:slug>/ci360.json", ExhibitCi360Manifest.as_view(), name="exhibit_ci360_manifest"),
]
