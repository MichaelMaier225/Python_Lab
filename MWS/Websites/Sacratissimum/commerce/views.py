"""HTTP handlers for bags, checkout and customer-owned orders."""

import logging
from smtplib import SMTPException

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import IntegrityError, OperationalError
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.debug import sensitive_variables
from django.views.decorators.http import require_POST
from stripe import SignatureVerificationError, StripeError

from store.models import ProductVariant

from .forms import QuantityForm
from .inventory import cart_rows, reserve_order
from .models import Order
from .notifications import send_receipt
from .payments import cancel_session, checkout_ready, process_event, stripe_session, verify_event
from .security import features, limited

logger = logging.getLogger(__name__)


@features
def bag(request):
    rows = cart_rows(request.session)
    return render(
        request,
        "commerce/bag.html",
        {
            "rows": rows,
            "subtotal": sum(r["total"] for r in rows),
            "checkout_ready": checkout_ready(),
        },
    )


@features
@require_POST
def bag_update(request, variant_id):
    if (
        request.user.is_authenticated
        and Order.objects.filter(customer=request.user, status__in=Order.OPEN_STATUSES).exists()
    ):
        messages.error(
            request,
            "An existing checkout holds these items. Cancel or complete it from Your account before changing your bag.",
        )
        return redirect("commerce:account")
    raw = dict(request.session.get("cart", {}))
    if request.POST.get("remove") == "true":
        raw.pop(str(variant_id), None)
    else:
        form = QuantityForm(request.POST)
        variant = get_object_or_404(
            ProductVariant.objects.select_related("product"),
            pk=variant_id,
            is_active=True,
            product__is_published=True,
            product__is_demo=False,
            product__availability="available",
        )
        if not form.is_valid():
            messages.error(request, "Choose a quantity between 1 and 20.")
        elif form.cleaned_data["quantity"] > variant.available_quantity:
            messages.error(
                request, "That quantity is unavailable. Please check the size and color again."
            )
        elif len(raw) >= 50 and str(variant_id) not in raw:
            messages.error(request, "Your bag contains too many different items.")
        else:
            raw[str(variant_id)] = form.cleaned_data["quantity"]
    request.session["cart"] = raw
    return redirect("commerce:bag")


@features
@login_required
@require_POST
def checkout(request):
    if not checkout_ready():
        return render(
            request,
            "commerce/notice.html",
            {
                "title": "Checkout is not open",
                "notice": "Purchasing is not available yet. Nothing has been charged.",
            },
            status=503,
        )
    if limited("checkout", str(request.user.pk), maximum=10):
        return HttpResponse("Please wait 15 minutes before retrying checkout.", status=429)
    pending = Order.objects.filter(customer=request.user, status__in=Order.OPEN_STATUSES).first()
    if pending and pending.expires_at <= timezone.now():
        messages.info(
            request,
            "Your earlier checkout is waiting for expiry confirmation. Please try later, or cancel it from Your account.",
        )
        return redirect("commerce:account")
    try:
        if pending is None:
            pending = reserve_order(request.user, cart_rows(request.session))
            request.session["pending_order"] = str(pending.reference)
        url = pending.checkout_url or stripe_session(pending)
    except IntegrityError:
        messages.info(
            request, "Another checkout is already open. Return to Your account to resume it."
        )
        return redirect("commerce:account")
    except ValidationError as error:
        messages.error(request, " ".join(error.messages))
        return redirect("commerce:bag")
    except (StripeError, OSError):
        logger.warning(
            "Stripe test checkout request failed. Existing reservations retained for safe reconciliation."
        )
        messages.error(
            request,
            "The payment service could not respond. Retry to resume the same checkout; nothing is marked paid here.",
        )
        return redirect("commerce:bag")
    response = HttpResponseRedirect(url)
    response.status_code = 303
    return response


@features
@login_required
def order_detail(request, reference):
    order = get_object_or_404(
        Order.objects.prefetch_related("items"), reference=reference, customer=request.user
    )
    if order.paid_at and request.session.get("pending_order") == str(order.reference):
        request.session.pop("pending_order", None)
        request.session["cart"] = {}
    # A browser redirect never confirms a payment or changes inventory.
    return render(request, "commerce/order.html", {"order": order})


@sensitive_variables("event", "order")
@csrf_exempt
@require_POST
def webhook(request):
    if settings.PREVIEW_MODE or not settings.CHECKOUT_ENABLED or not settings.STRIPE_WEBHOOK_SECRET:
        return HttpResponse(status=404)
    if len(request.body) > 262144:
        return HttpResponse(status=413)
    try:
        event = verify_event(request.body, request.headers.get("Stripe-Signature", ""))
    except (ValueError, SignatureVerificationError):
        return HttpResponse(status=400)
    try:
        order = process_event(event)
        send_receipt(order)
    except (
        ValidationError,
        IntegrityError,
        OperationalError,
        SMTPException,
        OSError,
        KeyError,
        TypeError,
    ):
        logger.warning(
            "Payment notification needs retry or owner review; payload and credentials not logged."
        )
        return HttpResponse(status=500)
    return HttpResponse(status=200)


@features
@login_required
@require_POST
def cancel_checkout(request, reference):
    order = get_object_or_404(Order, reference=reference, customer=request.user)
    if order.paid_at or order.released_at:
        return redirect("commerce:order", reference)
    if order.stripe_session_id and settings.STRIPE_SECRET_KEY:
        try:
            if cancel_session(order):
                messages.success(request, "Checkout canceled and stock released.")
        except (StripeError, ValidationError, OSError):
            messages.error(
                request,
                "Checkout could not be canceled. Payment may be processing; inventory has not been released.",
            )
    else:
        messages.info(
            request,
            "This checkout needs payment-service reconciliation before stock can be released.",
        )
    return redirect("commerce:order", reference)
