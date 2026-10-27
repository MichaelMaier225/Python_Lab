"""Transactional emails. No credentials or email tokens are logged."""

from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.views.decorators.debug import sensitive_variables

from .models import Order
from .security import verification_token


@sensitive_variables("token", "url")
def send_verification(user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = verification_token.make_token(user)
    url = settings.SITE_URL + reverse("commerce:verify", args=[uid, token])
    send_mail(
        "Verify your Sacratissimum account",
        f"Verify your email to activate your account:\n{url}\nThis link expires in one hour.",
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
    )


def send_receipt(order):
    if not order or not order.paid_at or order.confirmation_sent_at:
        return
    body = f"Your Sacratissimum test order {order.reference} is {order.get_status_display()}.\n"
    body += "\n".join(
        f"{i.quantity} × {i.product_name} ({i.color}, {i.size})" for i in order.items.all()
    )
    body += f"\nTotal: {order.currency.upper()} {order.total:.2f}\n{settings.SITE_URL}{order.get_absolute_url()}\n"
    body += "This is a test payment, not a live purchase.\n"
    if order.fulfillment_method == "pickup":
        body += settings.PICKUP_INSTRUCTIONS
    send_mail(
        "Sacratissimum — test order confirmation", body, settings.DEFAULT_FROM_EMAIL, [order.email]
    )
    Order.objects.filter(pk=order.pk, confirmation_sent_at__isnull=True).update(
        confirmation_sent_at=timezone.now()
    )
