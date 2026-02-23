# analyzer/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path("", views.landing, name="landing"),
    path("dashboard/", views.index, name="index"),
    path("history/", views.history, name="history"),
    path("results/<int:contract_id>/", views.results, name="results"),

    path("analyze-document/", views.analyze_document, name="analyze_document"),
    path("analyze-text/", views.analyze_text, name="analyze_text"),
    path("task-status/<str:task_id>/", views.task_status, name="task_status"),

    path("risk/<int:risk_id>/update/", views.update_risk, name="update_risk"),
    path("contract/<int:contract_id>/delete/", views.delete_contract, name="delete_contract"),
]