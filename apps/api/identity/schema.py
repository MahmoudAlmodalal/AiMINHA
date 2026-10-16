from typing import Any

from django.conf import settings
from drf_spectacular.extensions import OpenApiAuthenticationExtension


class SessionSchema(OpenApiAuthenticationExtension):
    target_class = "identity.security.IdentityAuthentication"
    name = "sessionCookie"

    def get_security_definition(self, auto_schema: Any) -> dict[str, str]:
        return {"type": "apiKey", "in": "cookie", "name": settings.SESSION_COOKIE_NAME}
