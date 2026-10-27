"""Account access policy, expiring verification tokens and persistent throttles."""

import hashlib
import hmac
from datetime import timedelta
from functools import wraps

from django.conf import settings
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.db import transaction
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.cache import never_cache

from .models import RequestLimit


def features(view):
    @wraps(view)
    @never_cache
    def wrapped(request, *args, **kwargs):
        if not settings.STORE_FEATURES_ENABLED:
            return render(
                request,
                "commerce/notice.html",
                {
                    "title": "This is a collection preview",
                    "notice": "Customer accounts and checkout are not open on this temporary preview.",
                },
                status=503,
            )
        return view(request, *args, **kwargs)

    return wrapped


def limit_key(action, identifier):
    return hmac.new(
        settings.SECRET_KEY.encode(), f"{action}:{identifier}".encode(), hashlib.sha256
    ).hexdigest()


def limited(action, identifier, maximum=5):
    key = limit_key(action, identifier)
    with transaction.atomic():
        row, _ = RequestLimit.objects.get_or_create(
            key=key, defaults={"window_start": timezone.now()}
        )
        row = RequestLimit.objects.select_for_update().get(pk=row.pk)
        if row.window_start < timezone.now() - timedelta(minutes=15):
            row.attempts = 0
            row.window_start = timezone.now()
        row.attempts += 1
        row.save(update_fields=["attempts", "window_start"])
        return row.attempts > maximum


class VerificationTokenGenerator(PasswordResetTokenGenerator):
    key_salt = "commerce.email-verification"

    def _make_hash_value(self, user, timestamp):
        return super()._make_hash_value(user, timestamp) + str(user.is_active)


verification_token = VerificationTokenGenerator()
