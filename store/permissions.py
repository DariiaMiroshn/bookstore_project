from rest_framework import permissions


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit or delete it.
    Read permissions are allowed to any request.
    """

    def has_object_permission(self, request, view, obj):
        # Дозволити безпечні HTTP методи (GET, HEAD, OPTIONS) для читання всім
        if request.method in permissions.SAFE_METHODS:
            return True

        # Запис, редагування або видалення дозволено лише власнику об'єкта
        # Якщо у моделі є пряме поле 'user'
        if hasattr(obj, "user"):
            return obj.user == request.user

        return False
