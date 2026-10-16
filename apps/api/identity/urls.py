from django.urls import path

from identity import views

urlpatterns = [
    path("session/csrf", views.CsrfView.as_view()),
    path("session/login", views.LoginView.as_view()),
    path("session", views.SessionView.as_view()),
    path("session/logout", views.LogoutView.as_view()),
    path("session/reauthentications", views.ReauthenticationView.as_view()),
    path("auth/registrations", views.RegistrationView.as_view()),
    path("auth/email-verifications", views.VerificationView.as_view()),
    path("auth/email-verification-requests", views.VerificationRequestView.as_view()),
    path("auth/password-reset-requests", views.ResetRequestView.as_view()),
    path("auth/password-resets", views.ResetView.as_view()),
    path("auth/google/authorizations", views.GoogleStartView.as_view()),
    path("auth/google/callbacks", views.GoogleCallbackView.as_view()),
    path("consents/disclosures", views.DisclosuresView.as_view()),
    path("consents", views.ConsentsView.as_view()),
    path("account/deletions", views.DeletionsView.as_view()),
    path("account/deletions/impact", views.DeletionImpactView.as_view()),
    path("account/recovery-requests", views.RecoveryRequestView.as_view()),
    path("account/restorations", views.RestorationsView.as_view()),
    path("files", views.FilesView.as_view()),
    path("files/<uuid:file_id>", views.FileView.as_view()),
    path("tickets/<uuid:ticket_id>/attachments", views.SharesView.as_view()),
    path("tickets/<uuid:ticket_id>/attachments/<uuid:attachment_id>", views.ShareView.as_view()),
]
