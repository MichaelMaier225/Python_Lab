from django.contrib.auth import views as auth
from django.urls import path, reverse_lazy

from . import accounts, views
from .security import features

app_name = "commerce"


def account_view(view, *, template_name="commerce/form.html", **options):
    """Apply the same preview/cache policy to Django's built-in account views."""
    return features(view.as_view(template_name=template_name, **options))


urlpatterns = [
    path("account/", accounts.account, name="account"),
    path("account/register/", accounts.register, name="register"),
    path(
        "account/login/",
        account_view(
            auth.LoginView,
            extra_context={"title": "Welcome back", "button": "Sign in", "login_page": True},
        ),
        name="login",
    ),
    path("account/logout/", auth.LogoutView.as_view(), name="logout"),
    path("account/verify/sent/", accounts.verification_sent, name="verification_sent"),
    path("account/verify/resend/", accounts.resend_verification, name="resend_verification"),
    path("account/verify/<uidb64>/<token>/", accounts.verify, name="verify"),
    path("account/security/", accounts.enroll_authenticator, name="security"),
    path(
        "account/password/change/",
        account_view(
            auth.PasswordChangeView,
            success_url=reverse_lazy("commerce:account"),
            extra_context={"title": "Change your password", "button": "Save password"},
        ),
        name="password_change",
    ),
    path("account/password-reset/", account_view(accounts.ResetPassword), name="password_reset"),
    path(
        "account/password-reset/sent/",
        account_view(
            auth.PasswordResetDoneView,
            template_name="commerce/notice.html",
            extra_context={
                "title": "Check your email",
                "notice": "If an active account exists, a reset link has been sent. Check your inbox.",
            },
        ),
        name="password_reset_done",
    ),
    path(
        "account/password-reset/<uidb64>/<token>/",
        account_view(
            auth.PasswordResetConfirmView,
            success_url=reverse_lazy("commerce:password_reset_complete"),
            extra_context={"title": "Choose a new password", "button": "Save password"},
        ),
        name="password_reset_confirm",
    ),
    path(
        "account/password-reset/complete/",
        account_view(
            auth.PasswordResetCompleteView,
            template_name="commerce/notice.html",
            extra_context={
                "title": "Password updated",
                "notice": "You can now sign in with your new password.",
            },
        ),
        name="password_reset_complete",
    ),
    path("account/orders/<uuid:reference>/", views.order_detail, name="order"),
    path("account/orders/<uuid:reference>/cancel/", views.cancel_checkout, name="cancel_checkout"),
    path("bag/", views.bag, name="bag"),
    path("bag/<int:variant_id>/", views.bag_update, name="bag_update"),
    path("checkout/", views.checkout, name="checkout"),
    path("payments/stripe/webhook/", views.webhook, name="webhook"),
]
