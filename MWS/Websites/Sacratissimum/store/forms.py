from django import forms

from .models import Inquiry, Product


class InquiryForm(forms.ModelForm):
    consent = forms.BooleanField(label="I agree to be contacted about this inquiry.")

    class Meta:
        model = Inquiry
        fields = ("name", "email", "business_name", "website", "product", "message")
        widgets = {"message": forms.Textarea(attrs={"rows": 5})}
        labels = {"website": "Store website (optional)", "message": "Tell us more (optional)"}

    def __init__(self, *args, kind, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.kind = kind
        if kind == Inquiry.Kind.WHOLESALE:
            del self.fields["product"]
            self.fields["business_name"].required = True
        else:
            del self.fields["business_name"]
            del self.fields["website"]
            self.fields["product"].queryset = Product.objects.filter(
                is_published=True, is_demo=False, preorder_interest=True
            )
            self.fields["product"].empty_label = "Future releases / no preference"
