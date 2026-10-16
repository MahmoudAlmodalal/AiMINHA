from __future__ import annotations

from typing import TYPE_CHECKING

from rest_framework.permissions import BasePermission
from rest_framework.request import Request

if TYPE_CHECKING:
    from rest_framework.views import APIView


class DenyAll(BasePermission):
    """New endpoints remain closed until their permissions are implemented."""

    def has_permission(self, request: Request, view: APIView) -> bool:
        return False
