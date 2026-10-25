from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class FrecargoUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("Operación FRECARGO", {"fields": ("role", "phone")}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("Operación FRECARGO", {"fields": ("first_name", "last_name", "role", "phone")}),)
    list_display = ("username", "first_name", "last_name", "role", "is_active", "is_superuser")
    list_filter = ("role", "is_active")

    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return False  # Desactivar cuentas preserva la atribución del historial.
