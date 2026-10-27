from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = "commerce"

class ConfirmPassword(views.FeatureMixin, auth_views.PasswordResetConfirmView):
    template_name = "commerce/form.html"
    success_url = "/account/password-reset/complete/"
    extra_context = {"title": "Choose a new password", "button": "Save password"}

class ChangePassword(views.FeatureMixin, auth_views.PasswordChangeView):
    template_name = "commerce/form.html"
    success_url = "/account/"
    extra_context = {"title": "Change your password", "button": "Save password"}

urlpatterns = [
    path("account/", views.account, name="account"),
    path("account/register/", views.register, name="register"),
    path("account/login/", views.SignIn.as_view(), name="login"),
    path("account/logout/", views.SignOut.as_view(), name="logout"),
    path("account/verify/sent/", views.verification_sent, name="verification_sent"),
    path("account/verify/resend/", views.resend_verification, name="resend_verification"),
    path("account/verify/<uidb64>/<token>/", views.verify, name="verify"),
    path("account/security/", views.security, name="security"),
    path("account/password/change/", ChangePassword.as_view(), name="password_change"),
    path("account/password-reset/", views.ResetPassword.as_view(), name="password_reset"),
    path("account/password-reset/sent/", views.features(auth_views.PasswordResetDoneView.as_view(template_name="commerce/notice.html", extra_context={"title": "Check your email", "notice": "If an active account exists, a reset link has been sent. Check your inbox."})), name="password_reset_done"),
    path("account/password-reset/<uidb64>/<token>/", ConfirmPassword.as_view(), name="password_reset_confirm"),
    path("account/password-reset/complete/", views.features(auth_views.PasswordResetCompleteView.as_view(template_name="commerce/notice.html", extra_context={"title": "Password updated", "notice": "You can now sign in with your new password."})), name="password_reset_complete"),
    path("account/orders/<uuid:reference>/", views.order_detail, name="order"),
    path("bag/", views.bag, name="bag"),
    path("bag/<int:variant_id>/", views.bag_update, name="bag_update"),
    path("account/orders/<uuid:reference>/cancel/", views.cancel_checkout, name="cancel_checkout"),
    path("checkout/", views.checkout, name="checkout"),
    path("payments/stripe/webhook/", views.webhook, name="webhook"),
]
