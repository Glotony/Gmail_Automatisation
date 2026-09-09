import secrets

from django.conf import settings
from rest_framework.permissions import BasePermission


class HasAPIKey(BasePermission):
    """
    Simple API-key authentication for our private automation API.
    """

    message = "Invalid or missing API key."

    def has_permission(self, request, view):
        supplied_key = request.headers.get(
            "X-API-Key",
            ""
        )

        configured_key = settings.API_KEY

        if not supplied_key or not configured_key:
            return False

        return secrets.compare_digest(
            supplied_key,
            configured_key,
        )