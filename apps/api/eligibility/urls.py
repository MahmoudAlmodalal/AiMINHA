from django.urls import path

from eligibility import views

urlpatterns = [
    path("profile", views.ProfileView.as_view()),
    path("eligibility/evaluations", views.EvaluationListView.as_view()),
    path("eligibility/evaluations/<uuid:evaluation_id>", views.EvaluationDetailView.as_view()),
    path("admin/scholarships/<uuid:scholarship_id>/eligibility-rules", views.RuleSetView.as_view()),
]
