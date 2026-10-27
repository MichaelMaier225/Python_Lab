"""Stock changes and checkout reservations; no payment-provider dependencies."""

from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from store.models import ProductVariant

from .models import InventoryMovement, Order, OrderItem


@transaction.atomic
def adjust_stock(variant_id, delta, reason, actor):
    if not delta or not reason.strip():
        raise ValidationError("Enter a non-zero adjustment and a reason.")
    variant = ProductVariant.objects.select_for_update().get(pk=variant_id)
    updated = ProductVariant.objects.filter(
        pk=variant.pk, stock_quantity__gte=F("reserved_quantity") - delta
    ).update(stock_quantity=F("stock_quantity") + delta)
    if not updated:
        raise ValidationError("Stock cannot be negative or lower than units reserved for checkout.")
    InventoryMovement.objects.create(
        variant=variant, delta=delta, reason=reason.strip(), actor=actor
    )


def cart_rows(session):
    raw = session.get("cart", {})
    if not isinstance(raw, dict):
        return []
    quantities = {
        int(k): int(v)
        for k, v in raw.items()
        if str(k).isdigit() and str(v).isdigit() and 1 <= int(v) <= 20
    }
    variants = (
        ProductVariant.objects.purchasable()
        .filter(pk__in=quantities)
        .select_related("product")
        .order_by("pk")
    )
    return [
        {
            "variant": v,
            "quantity": quantities[v.pk],
            "unit_price": v.product.price,
            "total": v.product.price * quantities[v.pk],
        }
        for v in variants
    ]


@transaction.atomic
def reserve_order(user, rows):
    if not rows:
        raise ValidationError("Your bag is empty or its products are no longer available.")
    order = Order.objects.create(
        customer=user,
        email=user.email,
        subtotal=Decimal("0"),
        expires_at=timezone.now() + timedelta(minutes=45),
        fulfillment_method=settings.STORE_FULFILLMENT,
        allowed_shipping_countries=list(settings.SHIPPING_COUNTRIES)
        if settings.STORE_FULFILLMENT == "shipping"
        else [],
        shipping=Decimal(settings.SHIPPING_RATE_CENTS) / 100
        if settings.STORE_FULFILLMENT == "shipping"
        else 0,
    )
    subtotal = Decimal("0")
    for row in sorted(rows, key=lambda r: r["variant"].pk):
        variant = (
            ProductVariant.objects.purchasable()
            .select_for_update()
            .select_related("product")
            .filter(pk=row["variant"].pk)
            .first()
        )
        quantity = row["quantity"]
        if variant is None or not 1 <= quantity <= 20:
            raise ValidationError("A selected product is no longer available.")
        updated = ProductVariant.objects.filter(
            pk=variant.pk, stock_quantity__gte=F("reserved_quantity") + quantity
        ).update(reserved_quantity=F("reserved_quantity") + quantity)
        if not updated:
            raise ValidationError(
                f"Not enough stock for {variant.product.name} — {variant.color}, {variant.size}."
            )
        OrderItem.objects.create(
            order=order,
            variant=variant,
            product_name=variant.product.name,
            size=variant.size,
            color=variant.color,
            sku=variant.sku or variant.barcode_value,
            quantity=quantity,
            unit_price=variant.product.price,
        )
        subtotal += variant.product.price * quantity
    if subtotal <= 0:
        raise ValidationError("Checkout requires a positive order subtotal.")
    order.subtotal = subtotal
    order.save(update_fields=["subtotal"])
    return order


def release_reservation(order):
    """Release once. The caller must hold the order lock in an atomic transaction."""
    if order.paid_at or order.released_at:
        return
    for item in order.items.select_related("variant").all():
        updated = ProductVariant.objects.filter(
            pk=item.variant_id, reserved_quantity__gte=item.quantity
        ).update(reserved_quantity=F("reserved_quantity") - item.quantity)
        if not updated:
            raise ValidationError("Reservation mismatch; manual inventory review required.")
    order.released_at = timezone.now()
    order.status = Order.Status.EXPIRED
    order.save(update_fields=["released_at", "status"])


def consume_reservation(order):
    """Caller holds the order lock; paid_at guards this mutation against replay."""
    for item in order.items.all():
        updated = ProductVariant.objects.filter(
            pk=item.variant_id,
            reserved_quantity__gte=item.quantity,
            stock_quantity__gte=item.quantity,
        ).update(
            stock_quantity=F("stock_quantity") - item.quantity,
            reserved_quantity=F("reserved_quantity") - item.quantity,
        )
        if not updated:
            raise ValidationError("Inventory reservation mismatch.")
        InventoryMovement.objects.create(
            variant_id=item.variant_id,
            delta=-item.quantity,
            reason="Stripe test payment confirmed",
            order=order,
        )
