"""Stripe test checkout and idempotent payment transitions."""

from decimal import Decimal
from urllib.parse import urlsplit

import stripe
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .inventory import consume_reservation, release_reservation
from .models import Order, PaymentEvent

stripe.api_version = "2026-09-30.endive"
stripe.default_http_client = stripe.RequestsClient(timeout=10)
stripe.max_network_retries = 1


def as_dict(value):
    return value.to_dict() if hasattr(value, "to_dict") else value


def checkout_ready():
    fulfillment = (
        settings.STORE_FULFILLMENT == "shipping"
        and settings.SHIPPING_COUNTRIES
        and settings.SHIPPING_RATE_CENTS >= 0
    ) or (settings.STORE_FULFILLMENT == "pickup" and settings.PICKUP_INSTRUCTIONS)
    return bool(
        settings.STORE_FEATURES_ENABLED
        and settings.CHECKOUT_ENABLED
        and not settings.PREVIEW_MODE
        and settings.STRIPE_SECRET_KEY
        and settings.STRIPE_WEBHOOK_SECRET
        and fulfillment
    )


def stripe_session(order):
    """The same order always uses the same Stripe idempotency key, including retries."""
    options = {
        "mode": "payment",
        "payment_method_types": ["card"],
        "customer_email": order.email,
        "client_reference_id": str(order.reference),
        "metadata": {"order_id": str(order.reference)},
        "payment_intent_data": {"metadata": {"order_id": str(order.reference)}},
        "line_items": [
            {
                "quantity": item.quantity,
                "price_data": {
                    "currency": "usd",
                    "unit_amount": int(item.unit_price * 100),
                    "product_data": {"name": f"{item.product_name} — {item.color}, {item.size}"},
                },
            }
            for item in order.items.all()
        ],
        "success_url": settings.SITE_URL + order.get_absolute_url() + "?checkout=returned",
        "cancel_url": settings.SITE_URL + order.get_absolute_url(),
        "expires_at": int(order.expires_at.timestamp()),
        "automatic_tax": {"enabled": True},
        "billing_address_collection": "required",
    }
    if order.fulfillment_method == "shipping":
        options["shipping_address_collection"] = {
            "allowed_countries": order.allowed_shipping_countries
        }
        options["shipping_options"] = [
            {
                "shipping_rate_data": {
                    "type": "fixed_amount",
                    "fixed_amount": {"amount": int(order.shipping * 100), "currency": "usd"},
                    "display_name": "Shipping",
                }
            }
        ]
    else:
        options["custom_text"] = {"submit": {"message": settings.PICKUP_INSTRUCTIONS[:1200]}}
    result = stripe.checkout.Session.create(
        **options, api_key=settings.STRIPE_SECRET_KEY, idempotency_key=f"checkout-{order.reference}"
    )
    result = as_dict(result)
    if result.get("livemode") is not False:
        raise ValidationError("Live payments are not supported by this version.")
    if urlsplit(result["url"]).hostname != "checkout.stripe.com" or not result["url"].startswith(
        "https://"
    ):
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


def _record_payment(order, session):
    if session.get("payment_status") != "paid":
        return
    details = session.get("total_details") or {}
    tax = details.get("amount_tax", 0)
    shipping = details.get("amount_shipping", 0)
    subtotal = session.get("amount_subtotal")
    if (
        session.get("currency") != order.currency
        or subtotal != int(order.subtotal * 100)
        or shipping != int(order.shipping * 100)
        or details.get("amount_discount", 0) != 0
        or not isinstance(tax, int)
        or tax < 0
        or session.get("amount_total") != subtotal + shipping + tax
        or (session.get("automatic_tax") or {}).get("status") != "complete"
    ):
        raise ValidationError("Paid amount, currency or tax status does not match the order.")
    intent = session.get("payment_intent")
    if not isinstance(intent, str) or not intent.startswith("pi_"):
        raise ValidationError("Missing payment reference.")
    if order.stripe_payment_intent and order.stripe_payment_intent != intent:
        raise ValidationError("Payment reference mismatch.")
    shipping_details = (
        (session.get("collected_information") or {}).get("shipping_details")
        or session.get("shipping_details")
        or {}
    )
    address = shipping_details.get("address") or {}
    if order.fulfillment_method == "shipping" and (
        address.get("country") not in order.allowed_shipping_countries
        or not address.get("line1")
        or not address.get("postal_code")
        or not shipping_details.get("name")
    ):
        raise ValidationError("Missing or unsupported shipping address.")
    if order.paid_at:
        return  # Duplicate or reordered notifications never deduct stock twice.
    if order.released_at:
        order.status = Order.Status.REVIEW  # Never oversell on an unexpected late payment.
    else:
        consume_reservation(order)
        order.status = Order.Status.PAID
    order.paid_at = timezone.now()
    order.tax = Decimal(tax) / 100
    order.total = Decimal(session["amount_total"]) / 100
    order.stripe_payment_intent = intent
    # Only fulfillment details; never store card data or a complete webhook payload.
    order.shipping_address = (
        {
            "name": str(shipping_details.get("name", ""))[:255],
            "address": {
                key: str(address.get(key) or "")[:255]
                for key in ("line1", "line2", "city", "state", "postal_code", "country")
            },
        }
        if order.fulfillment_method == "shipping"
        else {}
    )
    order.save()


def _record_refund(order, data):
    """Refunds change financial state; physical returns require staff adjustment."""
    if data.get("currency") != order.currency or data.get("amount") != int(order.total * 100):
        raise ValidationError("Refund amount does not match original charge.")
    refunded = data.get("amount_refunded", 0)
    if not 0 < refunded <= int(order.total * 100):
        raise ValidationError("Invalid refund amount.")
    if refunded >= int(order.refunded_amount * 100):
        order.refunded_amount = Decimal(refunded) / 100
        order.status = (
            Order.Status.REFUNDED
            if refunded == int(order.total * 100)
            else Order.Status.PART_REFUNDED
        )
        order.save(update_fields=["status", "refunded_amount"])


@transaction.atomic
def process_event(event):
    event = as_dict(event)
    if event.get("livemode") is not False:
        raise ValidationError("Live events are not accepted.")
    event_type = event["type"]
    if event_type not in {
        "checkout.session.completed",
        "checkout.session.async_payment_succeeded",
        "checkout.session.expired",
        "charge.refunded",
    }:
        return None
    data = event["data"]["object"]
    if data.get("livemode"):
        raise ValidationError("Live objects are not accepted.")
    if event_type == "charge.refunded":
        order = (
            Order.objects.select_for_update()
            .filter(stripe_payment_intent=data.get("payment_intent", ""))
            .first()
        )
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
    _, created = PaymentEvent.objects.get_or_create(
        event_id=event["id"], defaults={"event_type": event_type}
    )
    if not created:
        return order
    if event_type == "charge.refunded":
        _record_refund(order, data)
    else:
        if not order.stripe_session_id:
            order.stripe_session_id = data["id"]
            order.save(update_fields=["stripe_session_id"])
        if event_type.endswith("expired"):
            release_reservation(order)
        else:
            _record_payment(order, data)
    return order


def verify_event(payload, signature):
    return stripe.Webhook.construct_event(payload, signature, settings.STRIPE_WEBHOOK_SECRET)


def cancel_session(order):
    session = as_dict(
        stripe.checkout.Session.expire(order.stripe_session_id, api_key=settings.STRIPE_SECRET_KEY)
    )
    if session.get("status") != "expired":
        return False
    process_event(
        {
            "id": f"cancel_{session['id']}",
            "type": "checkout.session.expired",
            "livemode": False,
            "data": {"object": session},
        }
    )
    return True
