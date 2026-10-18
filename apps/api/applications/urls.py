from django.urls import path

from applications import views

urlpatterns = [
    path("applications", views.ApplicationsView.as_view()),
    path("applications/round-options", views.RoundOptionsView.as_view()),
    path("applications/<uuid:application_id>", views.ApplicationView.as_view()),
    path("applications/<uuid:application_id>/history", views.HistoryView.as_view()),
    path("applications/<uuid:application_id>/notes", views.NotesView.as_view()),
    path("applications/<uuid:application_id>/transitions", views.TransitionView.as_view()),
    path("applications/<uuid:application_id>/corrections", views.CorrectionView.as_view()),
    path("applications/<uuid:application_id>/rebase", views.RebaseView.as_view()),
    path("applications/<uuid:application_id>/requirements", views.RequirementsView.as_view()),
    path(
        "applications/<uuid:application_id>/requirements/<str:requirement_key>/artifact",
        views.ArtifactView.as_view(),
    ),
    path(
        "applications/<uuid:application_id>/artifact-options", views.ArtifactOptionsView.as_view()
    ),
    path(
        "applications/<uuid:application_id>/submitted-artifacts",
        views.SubmittedArtifactsView.as_view(),
    ),
    path(
        "applications/<uuid:application_id>/artifact-deletion-requests",
        views.DeletionRequestsView.as_view(),
    ),
    path("saved-scholarships", views.SavedScholarshipsView.as_view()),
    path("saved-scholarships/<uuid:scholarship_id>", views.SavedScholarshipView.as_view()),
]
