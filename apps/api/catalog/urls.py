from django.urls import path

from catalog import views

urlpatterns = [
    path("scholarships", views.PublicScholarshipListView.as_view()),
    path("scholarships/<uuid:scholarship_id>", views.PublicScholarshipDetailView.as_view()),
    path("admin/sources", views.SourceListView.as_view()),
    path("admin/sources/<uuid:source_id>/versions", views.SourceVersionView.as_view()),
    path("admin/scholarships", views.CandidateListView.as_view()),
    path("admin/scholarships/<uuid:scholarship_id>", views.CandidateDetailView.as_view()),
    path("admin/scholarships/<uuid:scholarship_id>/versions", views.CandidateVersionView.as_view()),
    path("admin/scholarships/<uuid:scholarship_id>/moderation", views.ModerationView.as_view()),
]
