from django.urls import path

from notifications.views import InboxView, MarkReadView, PreferenceView

urlpatterns = [
    path("notifications", InboxView.as_view(), name="notification-inbox"),
    path(
        "notifications/<uuid:notification_id>/read",
        MarkReadView.as_view(),
        name="notification-read",
    ),
    path("notification-preferences", PreferenceView.as_view(), name="notification-preferences"),
]
