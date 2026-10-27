"""Recover missed Stripe test notifications without releasing stock on guesses."""

from datetime import timedelta

import stripe
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from commerce.inventory import release_reservation
from commerce.models import Order
from commerce.notifications import send_receipt
from commerce.payments import as_dict, process_event


class Command(BaseCommand):
    help = (
        "Reconcile pending TEST checkouts and retry order emails; never blindly clear reservations."
    )

    def handle(self, *args, **options):
        if not settings.STRIPE_SECRET_KEY or settings.PREVIEW_MODE:
            raise CommandError("Configure a Stripe test key outside disposable preview mode first.")
        for order in Order.objects.filter(status__in=Order.OPEN_STATUSES).order_by("created_at"):
            session = None
            if order.stripe_session_id:
                session = as_dict(
                    stripe.checkout.Session.retrieve(
                        order.stripe_session_id, api_key=settings.STRIPE_SECRET_KEY
                    )
                )
            else:
                # Recover a create request whose response was lost. Exhaust the
                # authoritative provider list before considering a release.
                sessions = stripe.checkout.Session.list(
                    created={"gte": int(order.created_at.timestamp()) - 60},
                    limit=100,
                    api_key=settings.STRIPE_SECRET_KEY,
                )
                for candidate in sessions.auto_paging_iter():
                    candidate = as_dict(candidate)
                    if (candidate.get("metadata") or {}).get("order_id") == str(order.reference):
                        session = candidate
                        break
                if session is None and order.expires_at < timezone.now() - timedelta(minutes=5):
                    with transaction.atomic():
                        locked = Order.objects.select_for_update().get(pk=order.pk)
                        release_reservation(locked)
                    continue
            if session is None:
                continue
            if session.get("livemode"):
                raise CommandError("Refusing to process a live checkout.")
            if session.get("status") == "open" and order.expires_at < timezone.now():
                session = as_dict(
                    stripe.checkout.Session.expire(
                        session["id"], api_key=settings.STRIPE_SECRET_KEY
                    )
                )
            kind = (
                "checkout.session.completed"
                if session.get("payment_status") == "paid"
                else "checkout.session.expired"
                if session.get("status") == "expired"
                else None
            )
            if kind:
                process_event(
                    {
                        "id": f"reconcile_{session['id']}_{kind}",
                        "type": kind,
                        "livemode": False,
                        "data": {"object": session},
                    }
                )
        for order in Order.objects.filter(paid_at__isnull=False, confirmation_sent_at__isnull=True):
            send_receipt(order)
        self.stdout.write(
            self.style.SUCCESS("Stripe test reconciliation completed. No default accounts created.")
        )
