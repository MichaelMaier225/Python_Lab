import uuid
from decimal import Decimal
from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator


class CustomerProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    email = models.EmailField(unique=True)

    def __str__(self):
        return self.user.get_username()


class Order(models.Model):
    class Status(models.TextChoices):
        CREATING = "creating", "Preparing checkout"
        PENDING = "pending", "Awaiting payment"
        PAID = "paid", "Paid"
        EXPIRED = "expired", "Checkout expired"
        REVIEW = "review", "Payment received — needs review"
        REFUNDED = "refunded", "Refunded"
        PART_REFUNDED = "part_refunded", "Partially refunded"

    reference = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    email = models.EmailField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.CREATING)
    currency = models.CharField(max_length=3, default="usd")
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0"))])
    shipping = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    refunded_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    fulfillment_method = models.CharField(max_length=20)
    shipping_address = models.JSONField(default=dict, blank=True)
    allowed_shipping_countries = models.JSONField(default=list, blank=True)
    stripe_session_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    stripe_payment_intent = models.CharField(max_length=255, blank=True, db_index=True)
    checkout_url = models.URLField(max_length=1000, blank=True)
    expires_at = models.DateTimeField()
    paid_at = models.DateTimeField(null=True, blank=True)
    released_at = models.DateTimeField(null=True, blank=True)
    confirmation_sent_at = models.DateTimeField(null=True, blank=True)
    fulfilled_at = models.DateTimeField(null=True, blank=True)
    carrier = models.CharField(max_length=80, blank=True)
    tracking_number = models.CharField(max_length=120, blank=True)
    tracking_url = models.URLField(blank=True)
    staff_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["customer"], condition=models.Q(status__in=["creating", "pending"]), name="one_open_checkout_per_customer")]

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.fulfilled_at and (not self.paid_at or self.status == self.Status.REVIEW):
            raise ValidationError("Only a paid order can be marked fulfilled.")
        if self.tracking_url and not self.tracking_url.startswith("https://"):
            raise ValidationError("Tracking links must use HTTPS.")

    def __str__(self):
        return str(self.reference)


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    variant = models.ForeignKey("store.ProductVariant", on_delete=models.PROTECT)
    product_name = models.CharField(max_length=160)
    size = models.CharField(max_length=24)
    color = models.CharField(max_length=60)
    sku = models.CharField(max_length=80)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=9, decimal_places=2)

    @property
    def line_total(self):
        return self.unit_price * self.quantity


class InventoryMovement(models.Model):
    variant = models.ForeignKey("store.ProductVariant", on_delete=models.PROTECT)
    delta = models.IntegerField()
    reason = models.CharField(max_length=240)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    order = models.ForeignKey(Order, null=True, blank=True, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class PaymentEvent(models.Model):
    event_id = models.CharField(max_length=255, unique=True)
    event_type = models.CharField(max_length=100)
    processed_at = models.DateTimeField(auto_now_add=True)


class RequestLimit(models.Model):
    key = models.CharField(max_length=64, unique=True)
    attempts = models.PositiveIntegerField(default=0)
    window_start = models.DateTimeField()
