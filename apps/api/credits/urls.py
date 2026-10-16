from django.urls import path

from credits import views

urlpatterns = [
    path("wallet", views.WalletView.as_view()),
    path("wallet/entries", views.EntriesView.as_view()),
    path("operations", views.OperationsView.as_view()),
    path("operations/<uuid:operation_id>", views.OperationView.as_view()),
    path("admin/policies/credits", views.CreditPolicyView.as_view()),
]
