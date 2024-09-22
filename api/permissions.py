from rest_framework import permissions

class IsEventManager(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.role == 'event_manager'