from decimal import Decimal

from django.core.validators import MinValueValidator, FileExtensionValidator
from django.db import models
from django.urls import reverse


class Product(models.Model):
    class Availability(models.TextChoices):
        PREVIEW = "preview", "Preview only"
        AVAILABLE = "available", "Available"
        COMING_SOON = "coming_soon", "Coming soon"
        UNAVAILABLE = "unavailable", "Currently unavailable"

    name = models.CharField(max_length=160)
    slug = models.SlugField(unique=True)
    description = models.TextField(help_text="Describe the design and confirmed product details.")
    price = models.DecimalField(max_digits=9, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))], help_text="Price in USD.")
    availability = models.CharField(max_length=20, choices=Availability.choices, default=Availability.PREVIEW)
    is_published = models.BooleanField(default=False, help_text="Only published products appear on the website.")
    is_featured = models.BooleanField(default=False)
    is_demo = models.BooleanField(default=False, help_text="Show a prominent concept label; never sell this as real merchandise.")
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["display_order", "name"]
        constraints = [models.CheckConstraint(condition=models.Q(price__gte=0), name="product_price_nonnegative")]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("store:product", kwargs={"slug": self.slug})

    @property
    def primary_image(self):
        return next(iter(self.images.all()), None)

    @property
    def active_variants(self):
        return [variant for variant in self.variants.all() if variant.is_active]

    @property
    def colors(self):
        return list(dict.fromkeys(variant.color for variant in self.active_variants))

    @property
    def sizes(self):
        return list(dict.fromkeys(variant.size for variant in self.active_variants))


class ProductImage(models.Model):
    product = models.ForeignKey(Product, related_name="images", on_delete=models.CASCADE)
    image = models.ImageField(upload_to="products/%Y/%m/", validators=[FileExtensionValidator(["jpg", "jpeg", "png", "webp"])], help_text="Upload an owned or licensed JPG, PNG, or WebP. First image is the cover.")
    alt_text = models.CharField(max_length=240, help_text="Describe the garment, color, design, and view for screen readers.")
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "pk"]

    def __str__(self):
        return self.alt_text


class ProductVariant(models.Model):
    product = models.ForeignKey(Product, related_name="variants", on_delete=models.CASCADE)
    size = models.CharField(max_length=24, help_text="For example: S, M, L, XL.")
    color = models.CharField(max_length=60, help_text="For example: Warm ivory.")
    sku = models.CharField(max_length=80, blank=True, help_text="Optional internal reference; no stock tracking yet.")
    is_active = models.BooleanField(default=True, help_text="Display this size/color combination on the product page.")
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "pk"]
        constraints = [models.UniqueConstraint(fields=["product", "size", "color"], name="unique_product_size_color")]

    def __str__(self):
        return f"{self.product} — {self.color} / {self.size}"
