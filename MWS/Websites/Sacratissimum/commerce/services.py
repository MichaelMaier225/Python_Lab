"""Inventory and payment transitions. Card details are handled only by Stripe."""
from datetime import timedelta
from decimal import Decimal
from urllib.parse import urlsplit
import hashlib
import hmac

import stripe
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from .models import InventoryMovement, Order, OrderItem, PaymentEvent, RequestLimit
from store.models import ProductVariant

# Pin the webhook endpoint to this version in Stripe as well.
stripe.api_version = "2026-09-30.endive"
stripe.default_http_client = stripe.RequestsClient(timeout=10)
stripe.max_network_retries = 1

def as_dict(value):
    return value.to_dict() if hasattr(value, "to_dict") else value


def checkout_ready():
    fulfillment = (
        settings.STORE_FULFILLMENT == "shipping" and settings.SHIPPING_COUNTRIES
        and settings.SHIPPING_RATE_CENTS >= 0
    ) or (settings.STORE_FULFILLMENT == "pickup" and settings.PICKUP_INSTRUCTIONS)
    return bool(settings.STORE_FEATURES_ENABLED and settings.CHECKOUT_ENABLED
                and not settings.PREVIEW_MODE and settings.STRIPE_SECRET_KEY
                and settings.STRIPE_WEBHOOK_SECRET and fulfillment)


def limit_key(action, identifier):
    return hmac.new(settings.SECRET_KEY.encode(), f"{action}:{identifier}".encode(), hashlib.sha256).hexdigest()


def limited(action, identifier, maximum=5):
    key = limit_key(action, identifier)
    with transaction.atomic():
        row, _ = RequestLimit.objects.get_or_create(key=key, defaults={"window_start": timezone.now()})
        row = RequestLimit.objects.select_for_update().get(pk=row.pk)
        if row.window_start < timezone.now() - timedelta(minutes=15):
            row.attempts = 0
            row.window_start = timezone.now()
        row.attempts += 1
        row.save(update_fields=["attempts", "window_start"])
        return row.attempts > maximum


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
    InventoryMovement.objects.create(variant=variant, delta=delta, reason=reason.strip(), actor=actor)


def cart_rows(session):
    raw = session.get("cart", {})
    if not isinstance(raw, dict):
        return []
    quantities = {int(k): int(v) for k, v in raw.items()
                  if str(k).isdigit() and str(v).isdigit() and 1 <= int(v) <= 20}
    variants = ProductVariant.objects.filter(
        pk__in=quantities, is_active=True, product__is_published=True,
        product__is_demo=False, product__availability="available",
    ).select_related("product").order_by("pk")
    return [{"variant": v, "quantity": quantities[v.pk], "unit_price": v.product.price,
             "total": v.product.price * quantities[v.pk]} for v in variants]


@transaction.atomic
def reserve_order(user, rows):
    if not rows:
        raise ValidationError("Your bag is empty or its products are no longer available.")
    order = Order.objects.create(
        customer=user, email=user.email, subtotal=Decimal("0"),
        expires_at=timezone.now() + timedelta(minutes=45),
        fulfillment_method=settings.STORE_FULFILLMENT,
        allowed_shipping_countries=list(settings.SHIPPING_COUNTRIES) if settings.STORE_FULFILLMENT == "shipping" else [],
        shipping=Decimal(settings.SHIPPING_RATE_CENTS) / 100 if settings.STORE_FULFILLMENT == "shipping" else 0,
    )
    subtotal = Decimal("0")
    for row in sorted(rows, key=lambda r: r["variant"].pk):
        variant = ProductVariant.objects.select_for_update().select_related("product").get(pk=row["variant"].pk)
        quantity = row["quantity"]
        if not (1 <= quantity <= 20 and variant.is_active and variant.product.is_published
                and not variant.product.is_demo and variant.product.availability == "available"):
            raise ValidationError("A selected product is no longer available.")
        updated = ProductVariant.objects.filter(
            pk=variant.pk, stock_quantity__gte=F("reserved_quantity") + quantity
        ).update(reserved_quantity=F("reserved_quantity") + quantity)
        if not updated:
            raise ValidationError(f"Not enough stock for {variant.product.name} — {variant.color}, {variant.size}.")
        OrderItem.objects.create(
            order=order, variant=variant, product_name=variant.product.name,
            size=variant.size, color=variant.color, sku=variant.sku or variant.barcode_value,
            quantity=quantity, unit_price=variant.product.price,
        )
        subtotal += variant.product.price * quantity
    if subtotal <= 0:
        raise ValidationError("Checkout requires a positive order subtotal.")
    order.subtotal = subtotal
    order.save(update_fields=["subtotal"])
    return order


def stripe_session(order):
    """The same order always uses the same Stripe idempotency key, including retries."""
    options = {
        "mode": "payment", "payment_method_types": ["card"],
        "customer_email": order.email, "client_reference_id": str(order.reference),
        "metadata": {"order_id": str(order.reference)},
        "payment_intent_data": {"metadata": {"order_id": str(order.reference)}},
        "line_items": [{"quantity": item.quantity, "price_data": {
            "currency": "usd", "unit_amount": int(item.unit_price * 100),
            "product_data": {"name": f"{item.product_name} — {item.color}, {item.size}"},
        }} for item in order.items.all()],
        "success_url": settings.SITE_URL + f"/account/orders/{order.reference}/?checkout=returned",
        "cancel_url": settings.SITE_URL + f"/account/orders/{order.reference}/",
        "expires_at": int(order.expires_at.timestamp()),
        "automatic_tax": {"enabled": True}, "billing_address_collection": "required",
    }
    if order.fulfillment_method == "shipping":
        options["shipping_address_collection"] = {"allowed_countries": order.allowed_shipping_countries}
        options["shipping_options"] = [{"shipping_rate_data": {
            "type": "fixed_amount", "fixed_amount": {"amount": int(order.shipping * 100), "currency": "usd"},
            "display_name": "Shipping",
        }}]
    else:
        options["custom_text"] = {"submit": {"message": settings.PICKUP_INSTRUCTIONS[:1200]}}
    result = stripe.checkout.Session.create(
        **options, api_key=settings.STRIPE_SECRET_KEY, idempotency_key=f"checkout-{order.reference}"
    )
    result = as_dict(result)
    if result.get("livemode") is not False:
        raise ValidationError("Live payments are not supported by this version.")
    if urlsplit(result["url"]).hostname != "checkout.stripe.com" or not result["url"].startswith("https://"):
        raise ValidationError("The payment provider returned an invalid checkout address.")
    with transaction.atomic():
        locked = Order.objects.select_for_update().get(pk=order.pk)
        if locked.stripe_session_id and locked.stripe_session_id != result["id"]:
            raise ValidationError("Checkout reference mismatch.")
        locked.stripe_session_id = result["id"]
        locked.checkout_url = result["url"]
        if locked.status == Order.Status.CREATING:
            locked.status = Order.Status.PENDING
        locked.save(update_fields=["stripe_session_id", "checkout_url", "status"])
    return result["url"]


def _release(order):
    if order.paid_at or order.released_at:
        return
    for item in order.items.select_related("variant").all():
        updated = ProductVariant.objects.filter(pk=item.variant_id, reserved_quantity__gte=item.quantity).update(
            reserved_quantity=F("reserved_quantity") - item.quantity)
        if not updated:
            raise ValidationError("Reservation mismatch; manual inventory review required.")
    order.released_at = timezone.now()
    order.status = Order.Status.EXPIRED
    order.save(update_fields=["released_at", "status"])


def _complete(order, session):
    if session.get("payment_status") != "paid":
        return
    details = session.get("total_details") or {}
    tax = details.get("amount_tax", 0)
    shipping = details.get("amount_shipping", 0)
    subtotal = session.get("amount_subtotal")
    if (session.get("currency") != order.currency or subtotal != int(order.subtotal * 100)
            or shipping != int(order.shipping * 100) or details.get("amount_discount", 0) != 0
            or not isinstance(tax, int) or tax < 0
            or session.get("amount_total") != subtotal + shipping + tax
            or (session.get("automatic_tax") or {}).get("status") != "complete"):
        raise ValidationError("Paid amount, currency or tax status does not match the order.")
    intent = session.get("payment_intent")
    if not isinstance(intent, str) or not intent.startswith("pi_"):
        raise ValidationError("Missing payment reference.")
    if order.stripe_payment_intent and order.stripe_payment_intent != intent:
        raise ValidationError("Payment reference mismatch.")
    shipping_details = (session.get("collected_information") or {}).get("shipping_details") or session.get("shipping_details") or {}
    address = shipping_details.get("address") or {}
    if order.fulfillment_method == "shipping" and (
        address.get("country") not in order.allowed_shipping_countries
        or not address.get("line1") or not address.get("postal_code") or not shipping_details.get("name")
    ):
        raise ValidationError("Missing or unsupported shipping address.")
    if order.paid_at:
        return  # Duplicate or reordered notifications never deduct stock twice.
    if order.released_at:
        order.status = Order.Status.REVIEW  # Never oversell on an unexpected late payment.
    else:
        for item in order.items.all():
            updated = ProductVariant.objects.filter(
                pk=item.variant_id, reserved_quantity__gte=item.quantity, stock_quantity__gte=item.quantity
            ).update(stock_quantity=F("stock_quantity") - item.quantity,
                     reserved_quantity=F("reserved_quantity") - item.quantity)
            if not updated:
                raise ValidationError("Inventory reservation mismatch.")
            InventoryMovement.objects.create(variant_id=item.variant_id, delta=-item.quantity,
                reason="Stripe test payment confirmed", order=order)
        order.status = Order.Status.PAID
    order.paid_at = timezone.now()
    order.tax = Decimal(tax) / 100
    order.total = Decimal(session["amount_total"]) / 100
    order.stripe_payment_intent = intent
    # Only fulfillment details; never store card data or a complete webhook payload.
    order.shipping_address = {
        "name": str(shipping_details.get("name", ""))[:255],
        "address": {key: str(address.get(key) or "")[:255] for key in ("line1", "line2", "city", "state", "postal_code", "country")},
    } if order.fulfillment_method == "shipping" else {}
    order.save()


@transaction.atomic
def process_event(event):
    event = as_dict(event)
    if event.get("livemode") is not False:
        raise ValidationError("Live events are not accepted.")
    event_type = event["type"]
    if event_type not in {"checkout.session.completed", "checkout.session.async_payment_succeeded", "checkout.session.expired", "charge.refunded"}:
        return None
    data = event["data"]["object"]
    if data.get("livemode"):
        raise ValidationError("Live objects are not accepted.")
    if event_type == "charge.refunded":
        order = Order.objects.select_for_update().filter(stripe_payment_intent=data.get("payment_intent", "")).first()
        if not order or not order.paid_at:
            raise ValidationError("Payment not yet recorded; retry notification later.")
    else:
        reference = (data.get("metadata") or {}).get("order_id")
        try:
            order = Order.objects.select_for_update().get(reference=reference)
        except (Order.DoesNotExist, ValueError, ValidationError):
            raise ValidationError("Unknown order reference.")
        if order.stripe_session_id and order.stripe_session_id != data.get("id"):
            raise ValidationError("Checkout session does not match order.")
    _, created = PaymentEvent.objects.get_or_create(event_id=event["id"], defaults={"event_type": event_type})
    if not created:
        return order
    if event_type == "charge.refunded":
        if data.get("currency") != order.currency or data.get("amount") != int(order.total * 100):
            raise ValidationError("Refund amount does not match original charge.")
        refunded = data.get("amount_refunded", 0)
        if not 0 < refunded <= int(order.total * 100):
            raise ValidationError("Invalid refund amount.")
        if refunded >= int(order.refunded_amount * 100):
            order.refunded_amount = Decimal(refunded) / 100
            order.status = Order.Status.REFUNDED if refunded == int(order.total * 100) else Order.Status.PART_REFUNDED
            order.save(update_fields=["status", "refunded_amount"])
        # A refund is not a physical return: inventory changes require staff adjustment.
    else:
        if not order.stripe_session_id:
            order.stripe_session_id = data["id"]
            order.save(update_fields=["stripe_session_id"])
        if event_type.endswith("expired"):
            _release(order)
        else:
            _complete(order, data)
    return order


def send_receipt(order):
    if not order or not order.paid_at or order.confirmation_sent_at:
        return
    body = f"Your Sacratissimum test order {order.reference} is {order.get_status_display()}.\n"
    body += "\n".join(f"{i.quantity} × {i.product_name} ({i.color}, {i.size})" for i in order.items.all())
    body += f"\nTotal: {order.currency.upper()} {order.total:.2f}\n{settings.SITE_URL}/account/orders/{order.reference}/\n"
    body += "This is a test payment, not a live purchase.\n"
    if order.fulfillment_method == "pickup":
        body += settings.PICKUP_INSTRUCTIONS
    send_mail("Sacratissimum — test order confirmation", body, settings.DEFAULT_FROM_EMAIL, [order.email])
    Order.objects.filter(pk=order.pk, confirmation_sent_at__isnull=True).update(confirmation_sent_at=timezone.now())
