from django.urls import path

from ai_gateway.views import AICapabilitiesView

urlpatterns = [path("ai/capabilities", AICapabilitiesView.as_view())]
