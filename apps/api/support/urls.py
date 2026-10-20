from django.urls import path

from support import views

urlpatterns = [
    path("tickets", views.TicketsView.as_view(), name="support-tickets"),
    path("tickets/<uuid:ticket_id>", views.TicketView.as_view(), name="support-ticket"),
    path(
        "tickets/<uuid:ticket_id>/messages",
        views.MessagesView.as_view(),
        name="support-messages",
    ),
    path(
        "tickets/<uuid:ticket_id>/ai-replies",
        views.AiReplyView.as_view(),
        name="support-ai-reply",
    ),
    path(
        "tickets/<uuid:ticket_id>/transitions",
        views.TransitionView.as_view(),
        name="support-transition",
    ),
    path(
        "tickets/<uuid:ticket_id>/history",
        views.HistoryView.as_view(),
        name="support-history",
    ),
    path("tickets/<uuid:ticket_id>/sla", views.SlaView.as_view(), name="support-sla"),
    path("tickets/<uuid:ticket_id>/rating", views.RatingView.as_view(), name="support-rating"),
    path(
        "tickets/<uuid:ticket_id>/attachments",
        views.AttachmentsView.as_view(),
        name="support-attachments",
    ),
    path(
        "tickets/<uuid:ticket_id>/attachments/<uuid:attachment_id>",
        views.ShareDetailView.as_view(),
        name="support-attachment",
    ),
    path("admin/tickets", views.AdminQueueView.as_view(), name="admin-support-queue"),
    path(
        "admin/tickets/<uuid:ticket_id>/assignments",
        views.AdminAssignmentView.as_view(),
        name="admin-support-assignment",
    ),
    path(
        "admin/tickets/<uuid:ticket_id>/messages",
        views.AdminMessagesView.as_view(),
        name="admin-support-messages",
    ),
    path(
        "admin/tickets/<uuid:ticket_id>/transitions",
        views.AdminTransitionView.as_view(),
        name="admin-support-transition",
    ),
    path(
        "admin/tickets/<uuid:ticket_id>/classification",
        views.AdminClassificationView.as_view(),
        name="admin-support-classification",
    ),
    path(
        "admin/tickets/<uuid:ticket_id>/attachments",
        views.AdminAttachmentsView.as_view(),
        name="admin-support-attachments",
    ),
    path(
        "admin/tickets/<uuid:ticket_id>/sla",
        views.AdminSlaView.as_view(),
        name="admin-support-sla",
    ),
    path(
        "admin/support/metrics",
        views.AdminMetricsView.as_view(),
        name="admin-support-metrics",
    ),
    path("admin/policies/sla", views.AdminPolicyView.as_view(), name="admin-support-policy"),
    path(
        "admin/policies/sla/current",
        views.AdminPolicyCurrentView.as_view(),
        name="admin-support-policy-current",
    ),
]
