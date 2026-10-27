from django.contrib import admin
from .models import Product, ProductImage, ProductVariant


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
    list_filter = ("is_published", "is_demo", "availability", "is_featured")
    search_fields = ("name", "description", "variants__sku")
    prepopulated_fields = {"slug": ("name",)}
    inlines = (ProductImageInline, ProductVariantInline)
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        ("Product", {"fields": ("name", "slug", "description", "price", "availability")}),
        ("Website visibility", {"fields": ("is_published", "is_featured", "is_demo", "display_order")}),
        ("Record", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ("product", "alt_text", "display_order")
    search_fields = ("product__name", "alt_text")
    autocomplete_fields = ("product",)


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ("product", "size", "color", "sku", "is_active")
    list_filter = ("is_active", "size", "color")
    search_fields = ("product__name", "sku")
    autocomplete_fields = ("product",)


admin.site.site_header = "Sacratissimum · Studio"
admin.site.site_title = "Sacratissimum Studio"
admin.site.index_title = "Manage the collection"
