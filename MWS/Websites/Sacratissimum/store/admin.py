from barcode import Code128
from django.contrib import admin
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import path, reverse
from django.utils.html import format_html

from commerce.forms import StockAdjustmentForm
from commerce.inventory import adjust_stock

from .models import Inquiry, Product, ProductImage, ProductVariant


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 0


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 0
    readonly_fields = ("stock_quantity", "reserved_quantity", "barcode_value")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "availability", "is_published", "is_featured", "is_demo")
    list_filter = (
        "is_published",
        "is_demo",
        "availability",
        "is_featured",
        "audience",
        "preorder_interest",
    )
    search_fields = ("name", "description", "variants__sku")
    prepopulated_fields = {"slug": ("name",)}
    inlines = (ProductImageInline, ProductVariantInline)
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (
            "Product",
            {
                "fields": (
                    "name",
                    "slug",
                    "description",
                    "price",
                    "availability",
                    "audience",
                    "preorder_interest",
                )
            },
        ),
        (
            "Website visibility",
            {"fields": ("is_published", "is_featured", "is_demo", "display_order")},
        ),
        ("Record", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ("product", "alt_text", "display_order")
    search_fields = ("product__name", "alt_text")
    autocomplete_fields = ("product",)


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = (
        "product",
        "size",
        "color",
        "sku",
        "stock_quantity",
        "reserved_quantity",
        "is_active",
    )
    list_filter = ("is_active", "size", "color")
    search_fields = ("product__name", "sku", "size", "color")
    autocomplete_fields = ("product",)
    readonly_fields = ("stock_quantity", "reserved_quantity", "barcode_value", "stock_controls")

    def get_urls(self):
        return [
            path(
                "<int:object_id>/adjust-stock/",
                self.admin_site.admin_view(self.adjust_stock_view),
                name="store_productvariant_adjust",
            ),
            path(
                "<int:object_id>/barcode.svg",
                self.admin_site.admin_view(self.barcode_view),
                name="store_productvariant_barcode",
            ),
        ] + super().get_urls()

    def stock_controls(self, obj):
        if not obj.pk:
            return "Save this variant first."
        return format_html(
            '<a href="{}">Adjust stock</a> · <a href="{}">Download Code 128 label</a>',
            reverse("admin:store_productvariant_adjust", args=[obj.pk]),
            reverse("admin:store_productvariant_barcode", args=[obj.pk]),
        )

    def adjust_stock_view(self, request, object_id):
        variant = get_object_or_404(ProductVariant, pk=object_id)
        if not self.has_change_permission(request, variant):
            raise PermissionDenied
        form = StockAdjustmentForm(request.POST or None)
        if request.method == "POST" and form.is_valid():
            try:
                adjust_stock(
                    variant.pk,
                    form.cleaned_data["delta"],
                    form.cleaned_data["reason"],
                    request.user,
                )
                self.message_user(request, "Stock updated and recorded in the inventory journal.")
                return redirect("admin:store_productvariant_change", variant.pk)
            except ValidationError as error:
                form.add_error(None, error)
        return render(
            request,
            "commerce/stock_adjustment.html",
            {
                **self.admin_site.each_context(request),
                "form": form,
                "variant": variant,
                "title": "Adjust stock",
                "opts": self.model._meta,
            },
        )

    def barcode_view(self, request, object_id):
        variant = get_object_or_404(ProductVariant, pk=object_id)
        if not self.has_view_permission(request, variant):
            raise PermissionDenied
        response = HttpResponse(
            Code128(variant.barcode_value).render(), content_type="image/svg+xml"
        )
        response["Content-Disposition"] = f'attachment; filename="{variant.barcode_value}.svg"'
        response["Cache-Control"] = "no-store, private"
        return response

    def get_search_results(self, request, queryset, search_term):
        if search_term.startswith("SAC") and search_term[3:].isdigit():
            return queryset.filter(pk=int(search_term[3:])), False
        return super().get_search_results(request, queryset, search_term)


@admin.register(Inquiry)
class InquiryAdmin(admin.ModelAdmin):
    list_display = ("name", "kind", "business_name", "created_at", "reviewed")
    list_filter = ("kind", "reviewed")
    search_fields = ("name", "email", "business_name")
    readonly_fields = ("created_at",)
