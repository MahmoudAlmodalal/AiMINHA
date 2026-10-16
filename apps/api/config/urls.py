from core.views import HealthView
from django.urls import path

urlpatterns = [path("api/v1/health", HealthView.as_view(), name="health")]
handler400 = "core.errors.bad_request"
handler403 = "core.errors.forbidden"
handler404 = "core.errors.not_found"
handler500 = "core.errors.server_error"
