from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied

class IsSubscribedUser(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.user and request.user.is_authenticated:
            if request.user.status:
                return True
            else:
                raise PermissionDenied(detail="Please subscribe to the plan before adding to cart")
        return False

class IsStaff(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.user and request.user.is_authenticated:
            if request.user.is_staff:
                return True
            else:
                raise PermissionDenied(detail="You are not authorized to do this task")
        return False

class IsAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        return request.user and request.user.is_authenticated and request.user.is_superuser