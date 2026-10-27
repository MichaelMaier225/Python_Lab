from functools import wraps
from base64 import b32encode
import logging
from smtplib import SMTPException
from uuid import UUID

import stripe
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView, PasswordResetView
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db import IntegrityError, OperationalError
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.decorators.debug import sensitive_post_parameters, sensitive_variables
from django_otp.plugins.otp_totp.models import TOTPDevice
from .forms import OTPSetupForm, QuantityForm, RegistrationForm
from .models import Order
from .services import cart_rows, checkout_ready, limited, process_event, reserve_order, send_receipt, stripe_session, as_dict
from .tokens import verification_token
from store.models import ProductVariant

logger = logging.getLogger(__name__)


def features(view):
    @wraps(view)
    @never_cache
    def wrapped(request, *args, **kwargs):
        if not settings.STORE_FEATURES_ENABLED:
            return render(request, "commerce/notice.html", {"title": "This is a collection preview", "notice": "Customer accounts and checkout are not open on this temporary preview."}, status=503)
        return view(request, *args, **kwargs)
    return wrapped


class FeatureMixin:
    def dispatch(self, request, *args, **kwargs):
        if not settings.STORE_FEATURES_ENABLED:
            return features(lambda r: None)(request)
        response = super().dispatch(request, *args, **kwargs)
        response["Cache-Control"] = "no-store, private"
        return response


class SignIn(FeatureMixin, LoginView):
    template_name = "commerce/form.html"
    extra_context = {"title": "Welcome back", "button": "Sign in", "login_page": True}


class SignOut(LogoutView):
    pass


class ResetPassword(FeatureMixin, PasswordResetView):
    template_name = "commerce/form.html"
    email_template_name = "registration/password_reset_email.txt"
    subject_template_name = "registration/password_reset_subject.txt"
    success_url = "/account/password-reset/sent/"
    extra_context = {"title": "Reset your password", "button": "Send reset link"}

    def form_valid(self, form):
        if limited("password-reset", form.cleaned_data["email"].strip().lower()):
            return redirect(self.success_url)
        try:
            return super().form_valid(form)
        except (SMTPException, OSError):
            logger.warning("Password reset email delivery failed; no credential or token logged.")
            return redirect(self.success_url)


@sensitive_variables("token", "url")
def email_verification(request, user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = verification_token.make_token(user)
    url = settings.SITE_URL + reverse("commerce:verify", args=[uid, token])
    send_mail("Verify your Sacratissimum account", f"Verify your email to activate your account:\n{url}\nThis link expires in one hour.", settings.DEFAULT_FROM_EMAIL, [user.email])


@sensitive_post_parameters("password1", "password2")
@features
def register(request):
    form = RegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        if limited("registration", request.META.get("REMOTE_ADDR", "unknown"), maximum=10):
            form.add_error(None, "Too many attempts. Please wait 15 minutes and try again.")
        else:
            try:
                user = form.save()
                email_verification(request, user)
                return redirect("commerce:verification_sent")
            except IntegrityError:
                form.add_error(None, "Unable to create this account. Please try signing in.")
            except (SMTPException, OSError):
                messages.error(request, "Your account was saved but email could not be delivered. Use Resend verification to try again.")
                return redirect("commerce:verification_sent")
    return render(request, "commerce/form.html", {"form": form, "title": "Create your account", "button": "Create account", "registration_page": True})


@features
def verify(request, uidb64, token):
    try:
        user = get_user_model().objects.get(pk=urlsafe_base64_decode(uidb64).decode())
    except (ValueError, UnicodeError, get_user_model().DoesNotExist):
        user = None
    if user and verification_token.check_token(user, token):
        if request.method != "POST":
            return render(request, "commerce/form.html", {"title": "Verify your email", "button": "Activate account"})
        user.is_active = True
        user.save(update_fields=["is_active"])
        messages.success(request, "Email verified. You can now sign in.")
        return redirect("commerce:login")
    return render(request, "commerce/notice.html", {"title": "This link is invalid or expired", "notice": "Request another verification email and use its latest link.", "resend": True}, status=400)


@features
def resend_verification(request):
    from django import forms
    class EmailForm(forms.Form):
        email = forms.EmailField(label="Email address")
    form = EmailForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"].lower()
        if not limited("verification", email):
            user = get_user_model().objects.filter(email__iexact=email, is_active=False).first()
            if user:
                try:
                    email_verification(request, user)
                except (SMTPException, OSError):
                    logger.warning("Verification email delivery failed; no credential or token logged.")
        return redirect("commerce:verification_sent")
    return render(request, "commerce/form.html", {"form": form, "title": "Resend verification", "button": "Send verification link"})


@features
def verification_sent(request):
    return render(request, "commerce/notice.html", {"title": "Check your email", "notice": "If an account needs verification, an activation link has been sent. Links expire in one hour.", "resend": True})


@features
@login_required
def account(request):
    return render(request, "commerce/account.html", {"orders": Order.objects.filter(customer=request.user)})


@sensitive_variables("device", "manual_secret")
@sensitive_post_parameters("password", "token")
@features
@login_required
def security(request):
    if not request.user.is_staff:
        return HttpResponse(status=403)
    confirmed = TOTPDevice.objects.filter(user=request.user, confirmed=True).exists()
    if confirmed:
        return render(request, "commerce/notice.html", {"title": "Authenticator enabled", "notice": "Your authenticator is enrolled. Administrators must enter a fresh code at admin sign-in. Device replacement requires private administrator recovery."})
    device = TOTPDevice.objects.filter(user=request.user, confirmed=False).first()
    # Opening this page does not create a device or expose a seed without password confirmation.
    form = OTPSetupForm(request.POST or None)
    show_seed = False
    if request.method == "POST":
        if limited("otp-enroll", str(request.user.pk), maximum=10):
            form.add_error(None, "Too many attempts. Wait 15 minutes.")
        elif not request.user.check_password(request.POST.get("password", "")):
            form.add_error("password", "Confirm your current password.")
        else:
            if not device:
                device = TOTPDevice.objects.create(user=request.user, confirmed=False, name="Sacratissimum authenticator")
            show_seed = True
            if not request.POST.get("token"):
                form = OTPSetupForm()
            elif form.is_valid():
                if device.verify_token(form.cleaned_data["token"]):
                    device.confirmed = True
                    device.save(update_fields=["confirmed"])
                    messages.success(request, "Authenticator verified. Use its codes for admin sign-in.")
                    return redirect("commerce:account")
                form.add_error("token", "That code is invalid or was already used.")
    return render(request, "commerce/security.html", {"form": form, "device": device if show_seed else None, "manual_secret": b32encode(device.bin_key).decode() if show_seed else ""})


@features
def bag(request):
    rows = cart_rows(request.session)
    return render(request, "commerce/bag.html", {"rows": rows, "subtotal": sum(r["total"] for r in rows), "checkout_ready": checkout_ready()})


@features
@require_POST
def bag_update(request, variant_id):
    if request.user.is_authenticated and Order.objects.filter(customer=request.user, status__in=[Order.Status.CREATING, Order.Status.PENDING]).exists():
        messages.error(request, "An existing checkout holds these items. Cancel or complete it from Your account before changing your bag.")
        return redirect("commerce:account")
    raw = dict(request.session.get("cart", {}))
    if request.POST.get("remove") == "true":
        raw.pop(str(variant_id), None)
    else:
        form = QuantityForm(request.POST)
        variant = get_object_or_404(ProductVariant.objects.select_related("product"), pk=variant_id, is_active=True,
            product__is_published=True, product__is_demo=False, product__availability="available")
        if not form.is_valid():
            messages.error(request, "Choose a quantity between 1 and 20.")
        elif form.cleaned_data["quantity"] > variant.available_quantity:
            messages.error(request, "That quantity is unavailable. Please check the size and color again.")
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
        return render(request, "commerce/notice.html", {"title": "Checkout is not open", "notice": "Purchasing is not available yet. Nothing has been charged."}, status=503)
    if limited("checkout", str(request.user.pk), maximum=10):
        return HttpResponse("Please wait 15 minutes before retrying checkout.", status=429)
    pending = Order.objects.filter(customer=request.user,
        status__in=[Order.Status.CREATING, Order.Status.PENDING]).first()
    if pending and pending.expires_at <= timezone.now():
        messages.info(request, "Your earlier checkout is waiting for expiry confirmation. Please try later, or cancel it from Your account.")
        return redirect("commerce:account")
    try:
        if pending is None:
            pending = reserve_order(request.user, cart_rows(request.session))
            request.session["pending_order"] = str(pending.reference)
        url = pending.checkout_url or stripe_session(pending)
    except IntegrityError:
        messages.info(request, "Another checkout is already open. Return to Your account to resume it.")
        return redirect("commerce:account")
    except ValidationError as error:
        messages.error(request, " ".join(error.messages))
        return redirect("commerce:bag")
    except (stripe.StripeError, OSError):
        logger.warning("Stripe test checkout request failed. Existing reservations retained for safe reconciliation.")
        messages.error(request, "The payment service could not respond. Retry to resume the same checkout; nothing is marked paid here.")
        return redirect("commerce:bag")
    response = HttpResponseRedirect(url)
    response.status_code = 303
    return response


@features
@login_required
def order_detail(request, reference):
    order = get_object_or_404(Order.objects.prefetch_related("items"), reference=reference, customer=request.user)
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
        event = stripe.Webhook.construct_event(request.body, request.headers.get("Stripe-Signature", ""), settings.STRIPE_WEBHOOK_SECRET)
    except (ValueError, stripe.SignatureVerificationError):
        return HttpResponse(status=400)
    try:
        order = process_event(event)
        send_receipt(order)
    except (ValidationError, IntegrityError, OperationalError, SMTPException, OSError, KeyError, TypeError):
        logger.warning("Payment notification needs retry or owner review; payload and credentials not logged.")
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
            session = as_dict(stripe.checkout.Session.expire(order.stripe_session_id, api_key=settings.STRIPE_SECRET_KEY))
            if session.get("status") == "expired":
                process_event({"id": f"cancel_{session['id']}", "type": "checkout.session.expired", "livemode": False, "data": {"object": session}})
                messages.success(request, "Checkout canceled and stock released.")
        except (stripe.StripeError, ValidationError, OSError):
            messages.error(request, "Checkout could not be canceled. Payment may be processing; inventory has not been released.")
    else:
        messages.info(request, "This checkout needs payment-service reconciliation before stock can be released.")
    return redirect("commerce:order", reference)
