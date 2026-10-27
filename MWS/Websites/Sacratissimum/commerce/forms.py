from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from django.db import transaction
from .models import CustomerProfile


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(max_length=254, label="Email address")

    class Meta(UserCreationForm.Meta):
        fields = ("username", "email")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if CustomerProfile.objects.filter(email=email).exists() or get_user_model().objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Unable to register this email. Try signing in or resetting your password.")
        return email

    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.is_active = False
        user.save()
        CustomerProfile.objects.create(user=user, email=user.email)
        return user


class QuantityForm(forms.Form):
    quantity = forms.IntegerField(min_value=1, max_value=20, initial=1)


class StockAdjustmentForm(forms.Form):
    delta = forms.IntegerField(label="Units to add or remove", help_text="Positive to add stock; negative to remove it.")
    reason = forms.CharField(max_length=240)


class OTPSetupForm(forms.Form):
    password = forms.CharField(widget=forms.PasswordInput, label="Confirm your current password")
    token = forms.CharField(max_length=6, min_length=6, label="Authenticator code", widget=forms.TextInput(attrs={"inputmode": "numeric", "autocomplete": "one-time-code"}))
