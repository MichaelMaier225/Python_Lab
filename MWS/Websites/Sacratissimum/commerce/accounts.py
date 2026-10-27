"""Verified accounts and staff authenticator enrollment."""

import logging
from base64 import b32encode
from smtplib import SMTPException

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordResetView
from django.db import IntegrityError
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils.http import urlsafe_base64_decode
from django.views.decorators.debug import sensitive_post_parameters, sensitive_variables
from django_otp.plugins.otp_totp.models import TOTPDevice

from .forms import EmailForm, OTPSetupForm, RegistrationForm
from .models import Order
from .notifications import send_verification
from .security import features, limited, verification_token

logger = logging.getLogger(__name__)


class ResetPassword(PasswordResetView):
    template_name = "commerce/form.html"
    email_template_name = "registration/password_reset_email.txt"
    subject_template_name = "registration/password_reset_subject.txt"
    success_url = reverse_lazy("commerce:password_reset_done")
    extra_context = {"title": "Reset your password", "button": "Send reset link"}

    def form_valid(self, form):
        if limited("password-reset", form.cleaned_data["email"].strip().lower()):
            return redirect(self.success_url)
        try:
            return super().form_valid(form)
        except (SMTPException, OSError):
            logger.warning("Password reset email delivery failed; no credential or token logged.")
            return redirect(self.success_url)


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
                send_verification(user)
                return redirect("commerce:verification_sent")
            except IntegrityError:
                form.add_error(None, "Unable to create this account. Please try signing in.")
            except (SMTPException, OSError):
                messages.error(
                    request,
                    "Your account was saved but email could not be delivered. Use Resend verification to try again.",
                )
                return redirect("commerce:verification_sent")
    return render(
        request,
        "commerce/form.html",
        {
            "form": form,
            "title": "Create your account",
            "button": "Create account",
            "registration_page": True,
        },
    )


@features
def verify(request, uidb64, token):
    try:
        user = get_user_model().objects.get(pk=urlsafe_base64_decode(uidb64).decode())
    except (ValueError, UnicodeError, get_user_model().DoesNotExist):
        user = None
    if user and verification_token.check_token(user, token):
        if request.method != "POST":
            return render(
                request,
                "commerce/form.html",
                {"title": "Verify your email", "button": "Activate account"},
            )
        user.is_active = True
        user.save(update_fields=["is_active"])
        messages.success(request, "Email verified. You can now sign in.")
        return redirect("commerce:login")
    return render(
        request,
        "commerce/notice.html",
        {
            "title": "This link is invalid or expired",
            "notice": "Request another verification email and use its latest link.",
            "resend": True,
        },
        status=400,
    )


@features
def resend_verification(request):
    form = EmailForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"].lower()
        if not limited("verification", email):
            user = get_user_model().objects.filter(email__iexact=email, is_active=False).first()
            if user:
                try:
                    send_verification(user)
                except (SMTPException, OSError):
                    logger.warning(
                        "Verification email delivery failed; no credential or token logged."
                    )
        return redirect("commerce:verification_sent")
    return render(
        request,
        "commerce/form.html",
        {"form": form, "title": "Resend verification", "button": "Send verification link"},
    )


@features
def verification_sent(request):
    return render(
        request,
        "commerce/notice.html",
        {
            "title": "Check your email",
            "notice": "If an account needs verification, an activation link has been sent. Links expire in one hour.",
            "resend": True,
        },
    )


@features
@login_required
def account(request):
    return render(
        request, "commerce/account.html", {"orders": Order.objects.filter(customer=request.user)}
    )


@sensitive_variables("device", "manual_secret")
@sensitive_post_parameters("password", "token")
@features
@login_required
def enroll_authenticator(request):
    if not request.user.is_staff:
        return HttpResponse(status=403)
    confirmed = TOTPDevice.objects.filter(user=request.user, confirmed=True).exists()
    if confirmed:
        return render(
            request,
            "commerce/notice.html",
            {
                "title": "Authenticator enabled",
                "notice": "Your authenticator is enrolled. Administrators must enter a fresh code at admin sign-in. Device replacement requires private administrator recovery.",
            },
        )
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
                device = TOTPDevice.objects.create(
                    user=request.user, confirmed=False, name="Sacratissimum authenticator"
                )
            show_seed = True
            if not request.POST.get("token"):
                form = OTPSetupForm()
            elif form.is_valid():
                if device.verify_token(form.cleaned_data["token"]):
                    device.confirmed = True
                    device.save(update_fields=["confirmed"])
                    messages.success(
                        request, "Authenticator verified. Use its codes for admin sign-in."
                    )
                    return redirect("commerce:account")
                form.add_error("token", "That code is invalid or was already used.")
    return render(
        request,
        "commerce/security.html",
        {
            "form": form,
            "device": device if show_seed else None,
            "manual_secret": b32encode(device.bin_key).decode() if show_seed else "",
        },
    )
