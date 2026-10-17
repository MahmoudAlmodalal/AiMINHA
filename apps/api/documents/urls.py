from django.urls import path

from documents import views

urlpatterns = [
    path("documents", views.DocumentsView.as_view()),
    path("documents/capabilities", views.CapabilitiesView.as_view()),
    path("documents/generate", views.GenerationView.as_view()),
    path("documents/extract", views.ExtractionView.as_view()),
    path("documents/<uuid:document_id>", views.DocumentView.as_view()),
    path("documents/<uuid:document_id>/versions", views.VersionsView.as_view()),
    path("documents/<uuid:document_id>/restore", views.RestoreView.as_view()),
    path("documents/<uuid:document_id>/approvals", views.ApprovalView.as_view()),
    path("documents/<uuid:document_id>/exports", views.ExportView.as_view()),
    path("documents/<uuid:document_id>/compare", views.CompareView.as_view()),
]
