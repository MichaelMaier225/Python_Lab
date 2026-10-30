from decimal import Decimal

from django.core.validators import FileExtensionValidator, MinValueValidator
from django.db import models
from django.urls import reverse

from .validators import product_image_size


class Product(models.Model):
    class Availability(models.TextChoices):
        PREVIEW = "preview", "Preview only"
        AVAILABLE = "available", "Available"
        COMING_SOON = "coming_soon", "Coming soon"
        UNAVAILABLE = "unavailable", "Currently unavailable"

    class Audience(models.TextChoices):
        ADULT = "adult", "Adult"
        KIDS = "kids", "Kids"

    audience = models.CharField(max_length=10, choices=Audience.choices, default=Audience.ADULT)
    preorder_interest = models.BooleanField(
        default=False,
        help_text="Show on Preorders for interest registration only; no payment or reservation.",
    )
    name = models.CharField(max_length=160)
    slug = models.SlugField(unique=True)
    description = models.TextField(help_text="Describe the design and confirmed product details.")
    price = models.DecimalField(
        max_digits=9,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Price in USD.",
    )
    availability = models.CharField(
        max_length=20, choices=Availability.choices, default=Availability.PREVIEW
    )
    is_published = models.BooleanField(
        default=False, help_text="Only published products appear on the website."
    )
    is_featured = models.BooleanField(default=False)
    is_demo = models.BooleanField(
        default=False,
        help_text="Show a prominent concept label; never sell this as real merchandise.",
    )
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["display_order", "name"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(price__gte=0), name="product_price_nonnegative"
            )
        ]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("store:product", kwargs={"slug": self.slug})

    @property
    def placeholder_art(self):
        # Demo concepts get distinct original artwork. Real products retain a
        # neutral placeholder until the owner uploads genuine photography.
        art = {
            "demo-most-sacred": "most-sacred-tee/ivory",
            "demo-walk-in-faith": "walk-in-faith-tee/charcoal",
            "demo-abide": "abide-tee/stone",
        }
        if self.is_demo and self.slug in art:
            return f"clothing/faith-edit/{art[self.slug]}/front.svg"
        return "store/images/tee-placeholder.svg"

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
    image = models.ImageField(
        upload_to="products/%Y/%m/",
        validators=[FileExtensionValidator(["jpg", "jpeg", "png", "webp"]), product_image_size],
        help_text="Upload an owned or licensed JPG, PNG, or WebP. First image is the cover.",
    )
    alt_text = models.CharField(
        max_length=240,
        help_text="Describe the garment, color, design, and view for screen readers.",
    )
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "pk"]

    def __str__(self):
        return self.alt_text


class ProductVariant(models.Model):
    product = models.ForeignKey(Product, related_name="variants", on_delete=models.CASCADE)
    size = models.CharField(max_length=24, help_text="For example: S, M, L, XL.")
    color = models.CharField(max_length=60, help_text="For example: Warm ivory.")
    sku = models.CharField(
        max_length=80,
        blank=True,
        help_text="Your internal SKU. Each variant also has a unique internal barcode based on its ID.",
    )
    stock_quantity = models.PositiveIntegerField(
        default=0, help_text="Physical units. Use Adjust stock to change this with an audit trail."
    )
    reserved_quantity = models.PositiveIntegerField(default=0, editable=False)
    is_active = models.BooleanField(
        default=True, help_text="Display this size/color combination on the product page."
    )
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["product", "size", "color"], name="unique_product_size_color"
            ),
            models.CheckConstraint(
                condition=models.Q(stock_quantity__gte=models.F("reserved_quantity")),
                name="stock_covers_reservations",
            ),
        ]

    def __str__(self):
        return f"{self.product} — {self.color} / {self.size}"

    @property
    def available_quantity(self):
        return self.stock_quantity - self.reserved_quantity

    @property
    def barcode_value(self):
        # Internal Code 128 identifier, not a purchased GS1/UPC retail number.
        return f"SAC{self.pk:012d}" if self.pk else ""


class Inquiry(models.Model):
    class Kind(models.TextChoices):
        PREORDER = "preorder", "Preorder interest"
        WHOLESALE = "wholesale", "Wholesale application"

    kind = models.CharField(max_length=12, choices=Kind.choices)
    name = models.CharField(max_length=120)
    email = models.EmailField()
    business_name = models.CharField(max_length=160, blank=True)
    website = models.URLField(blank=True)
    product = models.ForeignKey(Product, null=True, blank=True, on_delete=models.SET_NULL)
    message = models.TextField(max_length=3000, blank=True)
    reviewed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_kind_display()} — {self.name}"
