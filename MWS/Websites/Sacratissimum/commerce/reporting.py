import re

from django.views.debug import SafeExceptionReporterFilter


class PrivateExceptionReporterFilter(SafeExceptionReporterFilter):
    # Database URLs contain passwords even though the setting name lacks PASSWORD.
    hidden_settings = re.compile(
        r"API|AUTH|TOKEN|KEY|SECRET|PASS|SIGNATURE|HTTP_COOKIE|DATABASE|STORAGE|EMAIL_HOST", re.I
    )
