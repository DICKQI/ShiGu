from __future__ import annotations

from rest_framework.permissions import BasePermission, SAFE_METHODS


def is_admin(user) -> bool:
    role = getattr(user, "role", None)
    role_name = getattr(role, "name", None)
    return str(role_name).lower() == "admin"


class IsAdminOrReadOnly(BasePermission):
    """
    SAFE: allowed for authenticated users (subject to view's other permissions).
    UNSAFE: only Admin.
    """

    def has_permission(self, request, view) -> bool:
        if request.method in SAFE_METHODS:
            return True
        return is_admin(request.user)


class IsOwnerOnly(BasePermission):
    """
    Object must belong to request.user for any operation.
    """

    def has_object_permission(self, request, view, obj) -> bool:
        if is_admin(request.user):
            return True
        return getattr(obj, "user_id", None) == getattr(request.user, "id", None)


class IsOwnerOrPublicReadOnly(BasePermission):
    """
    Read:
      - allow if obj.is_public True OR owner
    Write:
      - only owner
    """

    def has_object_permission(self, request, view, obj) -> bool:
        if is_admin(request.user):
            return True
        user_id = getattr(request.user, "id", None)
        owner_ok = getattr(obj, "user_id", None) == user_id
        if request.method in SAFE_METHODS:
            return bool(getattr(obj, "is_public", False)) or owner_ok
        return owner_ok

