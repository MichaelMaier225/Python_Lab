from datetime import timedelta
from decimal import Decimal
import hashlib
import hmac
import json
import re
import time
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from django_otp.oath import TOTP
from django_otp.plugins.otp_totp.models import TOTPDevice
from .models import InventoryMovement, Order, PaymentEvent
from .services import adjust_stock, cart_rows, checkout_ready, process_event, reserve_order, stripe_session
from store.models import Product, ProductVariant


@override_settings(STORE_FEATURES_ENABLED=True, EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", SITE_URL="http://testserver")
class AccountTests(TestCase):
    def test_registration_hashes_password_requires_verified_email(self):
        password = "a-private-test-password-927!"
        response = self.client.post(reverse("commerce:register"), {"username": "tanner", "email": "Tanner@Example.test", "password1": password, "password2": password})
        self.assertEqual(response.status_code, 302)
        user = get_user_model().objects.get(username="tanner")
        self.assertFalse(user.is_active)
        self.assertNotEqual(user.password, password)
        self.assertTrue(user.check_password(password))
        self.assertEqual(user.customerprofile.email, "tanner@example.test")
        self.client.post(reverse("commerce:login"), {"username": "tanner", "password": password})
        self.assertNotIn("_auth_user_id", self.client.session)
        link = re.search(r"http://testserver(/account/verify/[^\s]+)", mail.outbox[0].body).group(1)
        self.assertEqual(self.client.get(link).status_code, 200)
        self.assertEqual(self.client.post(link).status_code, 302)
        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertEqual(self.client.get(link).status_code, 400)
        response = self.client.post(reverse("commerce:login"), {"username": "tanner", "password": password})
        self.assertEqual(response.status_code, 302)
        self.assertIn("_auth_user_id", self.client.session)

    def test_duplicate_email_cannot_register(self):
        get_user_model().objects.create_user("existing", email="existing@example.test", password="secure-password-123!")
        response = self.client.post(reverse("commerce:register"), {"username": "new", "email": "EXISTING@example.test", "password1": "secure-password-123!", "password2": "secure-password-123!"})
        self.assertContains(response, "Unable to register this email")
        self.assertEqual(get_user_model().objects.count(), 1)

    def test_login_is_throttled_and_open_redirect_blocked(self):
        user = get_user_model().objects.create_user("customer", password="secure-password-123!")
        for _ in range(5):
            self.client.post(reverse("commerce:login"), {"username": "customer", "password": "wrong"})
        response = self.client.post(reverse("commerce:login"), {"username": "customer", "password": "secure-password-123!"})
        self.assertIn(response.status_code, (429, 302))
        self.assertNotIn("_auth_user_id", self.client.session)
        other = get_user_model().objects.create_user("other", password="secure-password-123!")
        response = self.client.post(reverse("commerce:login"), {"username": "other", "password": "secure-password-123!", "next": "https://attacker.example/"})
        self.assertNotIn("attacker", response.url)

    def test_username_throttle_normalizes_unicode_across_client_ips(self):
        get_user_model().objects.create_user("customer", password="secure-password-123!")
        for index in range(5):
            name = "customer" if index % 2 else "ｃｕｓｔｏｍｅｒ"
            self.client.post(reverse("commerce:login"), {"username": name, "password": "wrong"}, REMOTE_ADDR=f"192.0.2.{index + 1}")
        response = self.client.post(reverse("commerce:login"), {"username": "customer", "password": "secure-password-123!"}, REMOTE_ADDR="192.0.2.100")
        self.assertEqual(response.status_code, 429)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_logout_is_post_only(self):
        user = get_user_model().objects.create_user("customer", password="secure-password-123!")
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse("commerce:logout")).status_code, 405)
        self.assertEqual(self.client.post(reverse("commerce:logout")).status_code, 302)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_admin_login_requires_password_and_actual_totp(self):
        from django.contrib import admin
        from commerce.admin import StoreOTPAdminSite
        user = get_user_model().objects.create_superuser("otp-owner", "otp@example.test", "secure-test-password-123!")
        device = TOTPDevice.objects.create(user=user, confirmed=True)
        site = admin.site._wrapped
        original_class = site.__class__
        try:
            site.__class__ = StoreOTPAdminSite
            no_token = self.client.post(reverse("admin:login"), {"username": user.username, "password": "secure-test-password-123!"})
            self.assertEqual(no_token.status_code, 200)
            self.assertNotContains(no_token, "secure-test-password-123!")
            self.assertNotIn("_auth_user_id", self.client.session)
            totp = TOTP(device.bin_key, step=device.step, t0=device.t0, digits=device.digits, drift=device.drift)
            response = self.client.post(reverse("admin:login"), {"username": user.username, "password": "secure-test-password-123!", "otp_token": str(totp.token()).zfill(6), "next": "/admin/"})
            self.assertEqual(response.status_code, 302)
            self.assertEqual(self.client.get(reverse("admin:index")).status_code, 200)
        finally:
            site.__class__ = original_class

    def test_reset_email_does_not_reveal_account_or_password(self):
        user = get_user_model().objects.create_user("customer", email="person@example.test", password="secure-password-123!")
        known = self.client.post(reverse("commerce:password_reset"), {"email": user.email})
        unknown = self.client.post(reverse("commerce:password_reset"), {"email": "unknown@example.test"})
        self.assertEqual(known.status_code, unknown.status_code)
        self.assertEqual(known.url, unknown.url)
        self.assertEqual(len(mail.outbox), 1)
        self.assertNotIn("secure-password-123!", mail.outbox[0].body)
        self.assertIn("/account/password-reset/", mail.outbox[0].body)

    def test_password_reset_changes_hash_and_invalidates_existing_sessions(self):
        user = get_user_model().objects.create_user("reset-user", email="reset@example.test", password="old-test-password-123!")
        original = Client()
        original.force_login(user)
        self.client.post(reverse("commerce:password_reset"), {"email": user.email})
        link = re.search(r"https?://[^/]+(/account/password-reset/[^\s]+)", mail.outbox[0].body).group(1)
        response = self.client.get(link)
        self.assertEqual(response.status_code, 302)
        response = self.client.post(response.url, {"new_password1": "new-test-password-987!", "new_password2": "new-test-password-987!"})
        self.assertEqual(response.status_code, 302)
        user.refresh_from_db()
        self.assertTrue(user.check_password("new-test-password-987!"))
        self.assertFalse(user.check_password("old-test-password-123!"))
        self.assertEqual(original.get(reverse("commerce:account")).status_code, 302)

    def test_production_admin_requires_a_verified_otp_device(self):
        from django.test import RequestFactory
        from django_otp.admin import OTPAdminSite
        user = get_user_model().objects.create_user("admin-check", is_staff=True, password="test-password-123!")
        request = RequestFactory().get("/admin/")
        request.user = user
        user.is_verified = lambda: False
        self.assertFalse(OTPAdminSite().has_permission(request))
        user.is_verified = lambda: True
        self.assertTrue(OTPAdminSite().has_permission(request))

    def test_otp_seed_requires_staff_and_password(self):
        user = get_user_model().objects.create_user("staff", password="secure-password-123!", is_staff=True)
        self.client.force_login(user)
        route = reverse("commerce:security")
        self.assertNotContains(self.client.get(route), "otpauth://")
        self.assertNotContains(self.client.post(route, {"password": "wrong"}), "otpauth://")
        response = self.client.post(route, {"password": "secure-password-123!"})
        self.assertContains(response, "otpauth://")
        self.assertIn("no-store", response["Cache-Control"])
        device = TOTPDevice.objects.get(user=user)
        totp = TOTP(device.bin_key, step=device.step, t0=device.t0, digits=device.digits, drift=device.drift)
        response = self.client.post(route, {"password": "secure-password-123!", "token": str(totp.token()).zfill(6)})
        self.assertEqual(response.status_code, 302)
        device.refresh_from_db()
        self.assertTrue(device.confirmed)
        self.assertNotContains(self.client.get(route), "otpauth://")

    @override_settings(STORE_FEATURES_ENABLED=False)
    def test_preview_does_not_collect_accounts(self):
        response = self.client.post(reverse("commerce:register"), {"username": "public-preview-user"})
        self.assertEqual(response.status_code, 503)
        self.assertEqual(get_user_model().objects.count(), 0)


COMMERCE_SETTINGS = {
    "STORE_FEATURES_ENABLED": True, "PREVIEW_MODE": False, "CHECKOUT_ENABLED": True,
    "STRIPE_SECRET_KEY": "sk_test_placeholder_not_a_credential", "STRIPE_WEBHOOK_SECRET": "whsec_placeholder_not_a_credential",
    "STORE_FULFILLMENT": "shipping", "SHIPPING_COUNTRIES": ["US"], "SHIPPING_RATE_CENTS": 500,
    "SITE_URL": "https://testserver", "EMAIL_BACKEND": "django.core.mail.backends.locmem.EmailBackend",
}


@override_settings(**COMMERCE_SETTINGS)
class InventoryPaymentTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("buyer", email="buyer@example.test", password="secure-password-123!")
        self.other = get_user_model().objects.create_user("other", email="other@example.test", password="secure-password-123!")
        self.product = Product.objects.create(name="Real tee", slug="real-tee", description="Actual product", price=Decimal("30.00"), is_published=True, availability="available")
        self.variant = ProductVariant.objects.create(product=self.product, size="M", color="Ivory", stock_quantity=3)

    def order(self, user=None, quantity=2):
        return reserve_order(user or self.user, [{"variant": self.variant, "quantity": quantity}])

    def session(self, order, paid=True):
        return {"id": "cs_test_example", "livemode": False, "metadata": {"order_id": str(order.reference)},
            "payment_status": "paid" if paid else "unpaid", "status": "complete" if paid else "expired",
            "currency": "usd", "amount_subtotal": int(order.subtotal * 100),
            "amount_total": int(order.subtotal * 100) + 700,
            "total_details": {"amount_shipping": 500, "amount_tax": 200, "amount_discount": 0},
            "automatic_tax": {"status": "complete"}, "payment_intent": "pi_test_example",
            "collected_information": {"shipping_details": {"name": "Test Customer", "address": {"line1": "Test address", "postal_code": "00000", "country": "US"}}}}

    def event(self, order, kind="checkout.session.completed", event_id="evt_example", paid=True):
        return {"id": event_id, "type": kind, "livemode": False, "data": {"object": self.session(order, paid)}}

    def post_event(self, event, valid=True):
        payload = json.dumps(event)
        timestamp = int(time.time())
        signature = hmac.new(settings.STRIPE_WEBHOOK_SECRET.encode(), f"{timestamp}.{payload}".encode(), hashlib.sha256).hexdigest()
        return self.client.post(reverse("commerce:webhook"), payload, content_type="application/json",
            HTTP_STRIPE_SIGNATURE=f"t={timestamp},v1={signature if valid else 'wrong'}")

    def test_multi_item_reservation_rolls_back_fully_on_stock_failure(self):
        empty = ProductVariant.objects.create(product=self.product, size="L", color="Ivory", stock_quantity=0)
        with self.assertRaises(ValidationError):
            reserve_order(self.user, [{"variant": self.variant, "quantity": 1}, {"variant": empty, "quantity": 1}])
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.reserved_quantity, 0)
        self.assertEqual(Order.objects.count(), 0)

    @patch("commerce.services.stripe.checkout.Session.create")
    def test_lost_provider_response_retries_idempotently_without_extra_stock(self, create):
        import stripe
        create.side_effect = [stripe.APIConnectionError("Simulated connection failure"), {"id": "cs_test_example", "url": "https://checkout.stripe.com/test", "livemode": False}]
        session = self.client.session; session["cart"] = {str(self.variant.pk): 2}; session.save()
        self.client.force_login(self.user)
        self.assertEqual(self.client.post(reverse("commerce:checkout")).status_code, 302)
        self.assertEqual(self.client.post(reverse("commerce:checkout")).status_code, 303)
        self.assertEqual(Order.objects.count(), 1)
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.reserved_quantity, 2)
        self.assertEqual(create.call_args_list[0].kwargs["idempotency_key"], create.call_args_list[1].kwargs["idempotency_key"])

    def test_reservation_and_atomic_oversell_prevention(self):
        order = self.order()
        self.variant.refresh_from_db()
        self.assertEqual((self.variant.stock_quantity, self.variant.reserved_quantity), (3, 2))
        with self.assertRaises(ValidationError):
            self.order(user=self.other, quantity=2)
        self.assertEqual(Order.objects.count(), 1)
        with self.assertRaises(ValidationError):
            adjust_stock(self.variant.pk, -2, "count correction", self.user)
        adjust_stock(self.variant.pk, 4, "New shipment", self.user)
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock_quantity, 7)
        self.assertEqual(InventoryMovement.objects.count(), 1)

    def test_paid_webhook_decrements_once_and_duplicate_email_once(self):
        order = self.order()
        event = self.event(order)
        self.assertEqual(self.post_event(event).status_code, 200)
        self.assertEqual(self.post_event(event).status_code, 200)
        self.assertEqual(self.post_event(self.event(order, event_id="evt_second")).status_code, 200)
        self.variant.refresh_from_db(); order.refresh_from_db()
        self.assertEqual((self.variant.stock_quantity, self.variant.reserved_quantity), (1, 0))
        self.assertEqual(order.status, Order.Status.PAID)
        self.assertEqual(order.total, Decimal("67.00"))
        self.assertEqual(InventoryMovement.objects.filter(order=order).count(), 1)
        self.assertEqual(len(mail.outbox), 1)

    def test_invalid_signature_amount_currency_and_live_events_rejected(self):
        order = self.order()
        event = self.event(order)
        self.assertEqual(self.post_event(event, valid=False).status_code, 400)
        event["data"]["object"]["amount_total"] = 1
        self.assertEqual(self.post_event(event).status_code, 500)
        self.assertEqual(PaymentEvent.objects.count(), 0)
        event = self.event(order); event["livemode"] = True
        self.assertEqual(self.post_event(event).status_code, 500)
        event = self.event(order); event["data"]["object"]["currency"] = "eur"
        self.assertEqual(self.post_event(event).status_code, 500)
        self.variant.refresh_from_db(); self.assertEqual(self.variant.stock_quantity, 3)

    def test_expired_checkout_releases_but_late_payment_needs_review(self):
        order = self.order()
        process_event(self.event(order, kind="checkout.session.expired", event_id="evt_expired", paid=False))
        self.variant.refresh_from_db(); self.assertEqual(self.variant.reserved_quantity, 0)
        process_event(self.event(order))
        order.refresh_from_db(); self.variant.refresh_from_db()
        self.assertEqual(order.status, Order.Status.REVIEW)
        self.assertEqual(self.variant.stock_quantity, 3)

    def test_expiry_after_payment_cannot_release_twice(self):
        order = self.order()
        process_event(self.event(order))
        process_event(self.event(order, kind="checkout.session.expired", event_id="evt_expired", paid=False))
        self.variant.refresh_from_db(); self.assertEqual((self.variant.stock_quantity, self.variant.reserved_quantity), (1, 0))

    def test_refund_does_not_restock_or_regress_on_old_event(self):
        order = self.order(); process_event(self.event(order))
        refund = {"id": "evt_refund", "type": "charge.refunded", "livemode": False, "data": {"object": {
            "payment_intent": "pi_test_example", "currency": "usd", "amount": 6700, "amount_refunded": 6700}}}
        process_event(refund)
        refund["id"] = "evt_older_refund"; refund["data"]["object"]["amount_refunded"] = 1000
        process_event(refund)
        order.refresh_from_db(); self.variant.refresh_from_db()
        self.assertEqual(order.status, Order.Status.REFUNDED)
        self.assertEqual(order.refunded_amount, Decimal("67.00"))
        self.assertEqual(self.variant.stock_quantity, 1)

    def test_redirect_does_not_mark_order_paid_or_leak_to_other_customer(self):
        order = self.order(); self.client.force_login(self.user)
        response = self.client.get(reverse("commerce:order", args=[order.reference]) + "?checkout=returned")
        self.assertEqual(response.status_code, 200)
        order.refresh_from_db(); self.assertIsNone(order.paid_at)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(reverse("commerce:order", args=[order.reference])).status_code, 404)

    @patch("commerce.services.stripe.checkout.Session.create")
    def test_checkout_uses_database_prices_and_retries_same_session(self, create):
        create.return_value = {"id": "cs_test_example", "url": "https://checkout.stripe.com/test", "livemode": False}
        session = self.client.session; session["cart"] = {str(self.variant.pk): 2}; session.save()
        self.client.force_login(self.user)
        self.assertEqual(self.client.post(reverse("commerce:checkout"), {"price": "0.01"}).status_code, 303)
        self.assertEqual(self.client.post(reverse("commerce:checkout")).status_code, 303)
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(create.call_count, 1)
        self.assertEqual(create.call_args.kwargs["line_items"][0]["price_data"]["unit_amount"], 3000)
        self.assertIn("checkout-", create.call_args.kwargs["idempotency_key"])
        self.assertTrue(create.call_args.kwargs["automatic_tax"]["enabled"])
        self.assertEqual(create.call_args.kwargs["shipping_address_collection"]["allowed_countries"], ["US"])

    def test_demo_cannot_be_reserved_or_added_to_bag(self):
        self.product.is_demo = True; self.product.save()
        with self.assertRaises(ValidationError):
            self.order()
        self.assertEqual(self.client.post(reverse("commerce:bag_update", args=[self.variant.pk]), {"quantity": 1}).status_code, 404)

    @override_settings(SHIPPING_RATE_CENTS=-1)
    def test_unconfirmed_shipping_blocks_checkout(self):
        self.assertFalse(checkout_ready())
        self.client.force_login(self.user)
        self.assertEqual(self.client.post(reverse("commerce:checkout")).status_code, 503)
        self.assertEqual(Order.objects.count(), 0)

    @override_settings(PREVIEW_MODE=True)
    def test_preview_refuses_payment_webhooks(self):
        self.assertFalse(checkout_ready())
        self.assertEqual(self.client.post(reverse("commerce:webhook"), "{}", content_type="application/json").status_code, 404)

    def test_stock_database_constraint_and_single_open_checkout(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            ProductVariant.objects.filter(pk=self.variant.pk).update(reserved_quantity=4)
        self.order(quantity=1)
        with self.assertRaises(IntegrityError):
            self.order(quantity=1)

    def test_barcode_is_internal_unique_and_staff_only(self):
        other = ProductVariant.objects.create(product=self.product, size="L", color="Ivory")
        self.assertNotEqual(self.variant.barcode_value, other.barcode_value)
        url = reverse("admin:store_productvariant_barcode", args=[self.variant.pk])
        self.assertEqual(self.client.get(url).status_code, 302)
        self.user.is_staff = True; self.user.is_superuser = True; self.user.save(); self.client.force_login(self.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/svg+xml")
        self.assertIn(self.variant.barcode_value.encode(), response.content)

    @patch("commerce.views.stripe.checkout.Session.expire")
    def test_customer_cancellation_requires_provider_confirmation(self, expire):
        order = self.order()
        order.stripe_session_id = "cs_test_example"
        order.status = Order.Status.PENDING
        order.save()
        expire.return_value = self.session(order, paid=False)
        self.client.force_login(self.user)
        self.assertEqual(self.client.post(reverse("commerce:cancel_checkout", args=[order.reference])).status_code, 302)
        order.refresh_from_db(); self.variant.refresh_from_db()
        self.assertEqual(order.status, Order.Status.EXPIRED)
        self.assertEqual(self.variant.reserved_quantity, 0)

    def test_pending_checkout_prevents_bag_changes(self):
        self.order()
        self.client.force_login(self.user)
        response = self.client.post(reverse("commerce:bag_update", args=[self.variant.pk]), {"quantity": 1})
        self.assertRedirects(response, reverse("commerce:account"))

    def test_stock_adjustment_admin_records_actor_and_supports_barcode_search(self):
        self.user.is_staff = True
        self.user.is_superuser = True
        self.user.save()
        self.client.force_login(self.user)
        url = reverse("admin:store_productvariant_adjust", args=[self.variant.pk])
        self.assertContains(self.client.get(url), "Units to add or remove")
        response = self.client.post(url, {"delta": 4, "reason": "Counted incoming stock"})
        self.assertEqual(response.status_code, 302)
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock_quantity, 7)
        self.assertEqual(InventoryMovement.objects.get().actor, self.user)
        listing = self.client.get(reverse("admin:store_productvariant_changelist"), {"q": self.variant.barcode_value})
        self.assertEqual(listing.context["cl"].result_count, 1)

    def test_cart_and_account_posts_need_csrf(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post(reverse("commerce:bag_update", args=[self.variant.pk]), {"quantity": 1}).status_code, 403)
        self.assertEqual(client.post(reverse("commerce:register"), {"username": "attack"}).status_code, 403)
