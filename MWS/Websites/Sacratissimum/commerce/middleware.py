import unicodedata

from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from django.shortcuts import render

from .models import RequestLimit
from .security import limit_key, limited


class LoginThrottleMiddleware:
    """An account-level ceiling supplements Axes' username/IP protection.

    Uses REMOTE_ADDR only through Axes defaults; no arbitrary forwarded IP is trusted.
    Runs after CSRF validation, and also covers incorrect admin OTP attempts.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        if request.method == "POST" and request.path in {"/account/login/", "/admin/login/"}:
            username = unicodedata.normalize("NFKC", request.POST.get("username", "")[:150].strip())
            if username and limited("login", username):
                return render(request, "commerce/locked.html", status=429)


@receiver(user_logged_in)
def reset_login_limit(sender, request, user, **kwargs):
    RequestLimit.objects.filter(
        key=limit_key("login", unicodedata.normalize("NFKC", user.get_username().strip()))
    ).delete()
