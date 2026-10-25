from django.contrib import admin
from .models import Customer, Shipment, ShipmentEvent


class ReadOnlyAdmin(admin.ModelAdmin):
    actions = None

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Customer)
class CustomerAdmin(ReadOnlyAdmin):
    list_display = ("name", "phone", "active")
    search_fields = ("name",)


@admin.register(Shipment)
class ShipmentAdmin(ReadOnlyAdmin):
    list_display = ("tracking_code", "customer", "status", "courier", "created_at")
    list_filter = ("status",)
    search_fields = ("tracking_code", "external_reference")


@admin.register(ShipmentEvent)
class EventAdmin(ReadOnlyAdmin):
    list_display = ("shipment", "kind", "actor", "created_at")
    search_fields = ("shipment__tracking_code",)
