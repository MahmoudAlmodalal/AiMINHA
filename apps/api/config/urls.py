from core.views import HealthView
from django.urls import include, path

urlpatterns = [
    path("api/v1/health", HealthView.as_view(), name="health"),
    path("api/v1/", include("identity.urls")),
    path("api/v1/", include("private_files.urls")),
    path("api/v1/", include("documents.urls")),
    path("api/v1/", include("applications.urls")),
    path("api/v1/", include("notifications.urls")),
    path("api/v1/", include("catalog.urls")),
    path("api/v1/", include("eligibility.urls")),
    path("api/v1/", include("credits.urls")),
    path("api/v1/", include("ai_gateway.urls")),
    path("api/v1/", include("support.urls")),
]
handler400 = "core.errors.bad_request"
handler403 = "core.errors.forbidden"
handler404 = "core.errors.not_found"
handler500 = "core.errors.server_error"
