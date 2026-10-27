"""Production admin requires a password and a verified authenticator."""

from django.conf import settings
from django.contrib.admin import AdminSite
from django.contrib.admin.forms import AdminAuthenticationForm
from django_otp.admin import OTPAdminAuthenticationForm, OTPAdminSite
from django_otp.plugins.otp_totp.models import TOTPDevice


class StoreAdminOTPForm(OTPAdminAuthenticationForm):
    def _chosen_device(self, user):
        selected = super()._chosen_device(user)
        if selected or self.cleaned_data.get("otp_device"):
            return selected
        # Select exactly one known device; never try a token against every
        # device (which can throttle unrelated devices). Multiple devices
        # retain django-otp's explicit device-picker requirement.
        devices = list(TOTPDevice.objects.select_for_update().filter(user=user, confirmed=True)[:2])
        return devices[0] if len(devices) == 1 else None

    def _update_form(self, user):
        super()._update_form(user)
        self.fields["password"].widget.render_value = False


class StoreAdminSite(AdminSite):
    site_header = "Sacratissimum · Studio"
    site_title = "Sacratissimum Studio"
    index_title = "Manage the collection"

    @property
    def login_form(self):
        return StoreAdminOTPForm if settings.ADMIN_REQUIRE_OTP else AdminAuthenticationForm

    @property
    def login_template(self):
        return OTPAdminSite.login_template if settings.ADMIN_REQUIRE_OTP else None

    def has_permission(self, request):
        return super().has_permission(request) and (
            not settings.ADMIN_REQUIRE_OTP or request.user.is_verified()
        )
