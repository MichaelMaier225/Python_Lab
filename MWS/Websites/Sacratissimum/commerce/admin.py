from django.conf import settings
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.http import HttpResponse
from django.urls import path, reverse
from django.utils.html import format_html
from django_otp.admin import OTPAdminSite, OTPAdminAuthenticationForm
from django_otp.plugins.otp_totp.models import TOTPDevice
from barcode import Code128
from .forms import StockAdjustmentForm
from .models import CustomerProfile, InventoryMovement, Order, OrderItem, PaymentEvent
from .services import adjust_stock
from store.admin import ProductVariantAdmin
from store.models import ProductVariant

class StoreAdminOTPForm(OTPAdminAuthenticationForm):
    def _chosen_device(self, user):
        selected = super()._chosen_device(user)
        if selected or self.cleaned_data.get("otp_device"):
            return selected
        # Select exactly one known device; never try a token against every
        # device (which can throttle unrelated devices). Multiple devices
        # retain django-otp's explicit device-picker requirement.
        devices = list(TOTPDevice.objects.select_for_update().filter(user=user, confirmed=True)[:2])
        return devices[0] if len(devices) == 1 else None

    def _update_form(self, user):
        super()._update_form(user)
        self.fields["password"].widget.render_value = False


class StoreOTPAdminSite(OTPAdminSite):
    login_form = StoreAdminOTPForm


# Existing registrations stay intact. Production staff must supply an OTP code.
if settings.ADMIN_REQUIRE_OTP:
    admin.site.__class__ = StoreOTPAdminSite


def variant_urls(self):
    return [
        path("<int:object_id>/adjust-stock/", self.admin_site.admin_view(self.adjust_stock_view), name="store_productvariant_adjust"),
        path("<int:object_id>/barcode.svg", self.admin_site.admin_view(self.barcode_view), name="store_productvariant_barcode"),
    ] + super(InventoryVariantAdmin, self).get_urls()


def stock_controls(self, obj):
    if not obj.pk:
        return "Save this variant first."
    return format_html('<a href="{}">Adjust stock</a> · <a href="{}">Download Code 128 label</a>',
        reverse("admin:store_productvariant_adjust", args=[obj.pk]), reverse("admin:store_productvariant_barcode", args=[obj.pk]))


def adjust_stock_view(self, request, object_id):
    variant = get_object_or_404(ProductVariant, pk=object_id)
    if not self.has_change_permission(request, variant):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied
    form = StockAdjustmentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            adjust_stock(variant.pk, form.cleaned_data["delta"], form.cleaned_data["reason"], request.user)
            self.message_user(request, "Stock updated and recorded in the inventory journal.")
            return redirect("admin:store_productvariant_change", variant.pk)
        except ValidationError as error:
            form.add_error(None, error)
    return render(request, "commerce/stock_adjustment.html", {
        **self.admin_site.each_context(request), "form": form, "variant": variant, "title": "Adjust stock", "opts": self.model._meta,
    })


def barcode_view(self, request, object_id):
    variant = get_object_or_404(ProductVariant, pk=object_id)
    if not self.has_view_permission(request, variant):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied
    response = HttpResponse(Code128(variant.barcode_value).render(), content_type="image/svg+xml")
    response["Content-Disposition"] = f'attachment; filename="{variant.barcode_value}.svg"'
    response["Cache-Control"] = "no-store, private"
    return response


class InventoryVariantAdmin(ProductVariantAdmin):
    get_urls = variant_urls
    adjust_stock_view = adjust_stock_view
    barcode_view = barcode_view
    stock_controls = stock_controls
    search_fields = ("product__name", "sku", "size", "color")
    def get_search_results(self, request, queryset, search_term):
        if search_term.startswith("SAC") and search_term[3:].isdigit():
            return queryset.filter(pk=int(search_term[3:])), False
        return super().get_search_results(request, queryset, search_term)

    readonly_fields = ("stock_quantity", "reserved_quantity", "barcode_value", "stock_controls")
    list_display = ("product", "size", "color", "sku", "stock_quantity", "reserved_quantity", "is_active")

admin.site.unregister(ProductVariant)
admin.site.register(ProductVariant, InventoryVariantAdmin)



class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    can_delete = False
    readonly_fields = ("variant", "product_name", "size", "color", "sku", "quantity", "unit_price")
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("reference", "customer", "status", "total", "fulfillment_method", "fulfilled_at", "created_at")
    list_filter = ("status", "fulfillment_method", "fulfilled_at")
    search_fields = ("reference", "email", "tracking_number")
    inlines = (OrderItemInline,)
    readonly_fields = tuple(f.name for f in Order._meta.fields if f.name not in {"fulfilled_at", "carrier", "tracking_number", "tracking_url", "staff_notes"})
    def has_add_permission(self, request):
        return False
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(InventoryMovement)
class InventoryMovementAdmin(admin.ModelAdmin):
    list_display = ("variant", "delta", "reason", "actor", "order", "created_at")
    readonly_fields = tuple(f.name for f in InventoryMovement._meta.fields)
    def has_add_permission(self, request):
        return False
    def has_delete_permission(self, request, obj=None):
        return False
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(CustomerProfile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "email")
    readonly_fields = ("user", "email")
    search_fields = ("email", "user__username")
    def has_add_permission(self, request):
        return False
    def has_delete_permission(self, request, obj=None):
        return False
