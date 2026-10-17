from django.urls import path

from private_files import views

urlpatterns = [
    path("files/capabilities", views.CapabilitiesView.as_view()),
    path("files/uploads", views.UploadView.as_view()),
    path("files/<uuid:file_id>/access-grants", views.GrantView.as_view()),
    path("files/<uuid:file_id>/content", views.ContentView.as_view()),
    path("files/<uuid:file_id>/storage", views.DeleteView.as_view()),
    path(
        "tickets/<uuid:ticket_id>/attachments/<uuid:attachment_id>/access-grants",
        views.TicketGrantView.as_view(),
    ),
    path(
        "tickets/<uuid:ticket_id>/attachments/<uuid:attachment_id>/content",
        views.TicketContentView.as_view(),
    ),
]
