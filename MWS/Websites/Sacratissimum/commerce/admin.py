from django.contrib import admin

from .models import CustomerProfile, InventoryMovement, Order, OrderItem


class ExistingRecordsAdmin(admin.ModelAdmin):
    """Records are created by application workflows, not admin buttons."""

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class ReadOnlyAdmin(ExistingRecordsAdmin):
    def has_change_permission(self, request, obj=None):
        return False


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    can_delete = False
    readonly_fields = ("variant", "product_name", "size", "color", "sku", "quantity", "unit_price")

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(ExistingRecordsAdmin):
    list_display = (
        "reference",
        "customer",
        "status",
        "total",
        "fulfillment_method",
        "fulfilled_at",
        "created_at",
    )
    list_filter = ("status", "fulfillment_method", "fulfilled_at")
    search_fields = ("reference", "email", "tracking_number")
    inlines = (OrderItemInline,)
    readonly_fields = tuple(
        f.name
        for f in Order._meta.fields
        if f.name
        not in {"fulfilled_at", "carrier", "tracking_number", "tracking_url", "staff_notes"}
    )


@admin.register(InventoryMovement)
class InventoryMovementAdmin(ReadOnlyAdmin):
    list_display = ("variant", "delta", "reason", "actor", "order", "created_at")
    readonly_fields = tuple(f.name for f in InventoryMovement._meta.fields)


@admin.register(CustomerProfile)
class ProfileAdmin(ReadOnlyAdmin):
    list_display = ("user", "email")
    readonly_fields = ("user", "email")
    search_fields = ("email", "user__username")
