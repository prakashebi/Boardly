from rest_framework.permissions import BasePermission

from core.models import UserRole


class IsAuthenticated(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and hasattr(request.user, 'id'))


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and hasattr(request.user, 'role') and request.user.role == UserRole.ADMIN)


class IsActive(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and hasattr(request.user, 'is_active') and request.user.is_active)


class IsAdminOrMember(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not hasattr(request.user, 'role'):
            return False
        return request.user.role in [UserRole.ADMIN, UserRole.MEMBER]


class CanWriteContent(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not hasattr(request.user, 'role'):
            return False
        return request.user.role != UserRole.VIEWER
