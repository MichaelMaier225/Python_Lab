from django.test import Client, TestCase, override_settings
from django.urls import reverse

from .models import Inquiry, Product


@override_settings(STORE_FEATURES_ENABLED=True)
class CollectionExpansionTests(TestCase):
    def setUp(self):
        self.kid = Product.objects.create(
            name="Kids approved tee",
            slug="kids-approved",
            price=20,
            audience="kids",
            is_published=True,
        )
        self.upcoming = Product.objects.create(
            name="Upcoming tee",
            slug="upcoming",
            price=25,
            is_published=True,
            preorder_interest=True,
        )
        self.private = Product.objects.create(
            name="Secret concept", slug="secret", price=25, audience="kids", preorder_interest=True
        )
        self.demo = Product.objects.create(
            name="Demo tee",
            slug="demo",
            price=25,
            is_published=True,
            is_demo=True,
            preorder_interest=True,
        )

    def test_kids_only_lists_published_kids(self):
        response = self.client.get(reverse("store:kids"))
        self.assertContains(response, self.kid.name)
        self.assertNotContains(response, self.private.name)
        self.assertNotContains(response, self.upcoming.name)

    def test_preorders_only_lists_published_real_upcoming_products(self):
        response = self.client.get(reverse("store:preorders"))
        self.assertContains(response, self.upcoming.name)
        self.assertNotContains(response, self.private.name)
        self.assertNotContains(response, self.demo.name)
        self.assertContains(response, "No payment is collected")

    def test_interest_is_persisted_and_redirect_prevents_refresh_duplicates(self):
        response = self.client.post(
            reverse("store:preorders"),
            {
                "name": "Alex",
                "email": "alex@example.com",
                "consent": "on",
                "product": self.upcoming.pk,
                "message": "Interested in medium",
            },
        )
        self.assertRedirects(response, reverse("store:preorders"))
        inquiry = Inquiry.objects.get()
        self.assertEqual(inquiry.kind, Inquiry.Kind.PREORDER)
        self.assertEqual(inquiry.product, self.upcoming)
        self.client.get(response.url)
        self.assertEqual(Inquiry.objects.count(), 1)

    def test_private_and_demo_products_cannot_be_submitted(self):
        for item in (self.private, self.demo, self.kid):
            self.client.post(
                reverse("store:preorders"),
                {
                    "name": "Alex",
                    "email": "alex@example.com",
                    "consent": "on",
                    "product": item.pk,
                },
            )
        self.assertFalse(Inquiry.objects.exists())

    def test_wholesale_requires_business_and_consent(self):
        payload = {"name": "Alex", "email": "alex@example.com"}
        self.client.post(reverse("store:wholesale"), payload)
        self.assertFalse(Inquiry.objects.exists())
        payload.update(
            business_name="Example boutique", consent="on", website="https://example.com"
        )
        self.assertRedirects(
            self.client.post(reverse("store:wholesale"), payload), reverse("store:wholesale")
        )
        self.assertEqual(Inquiry.objects.get().kind, Inquiry.Kind.WHOLESALE)

    def test_repeat_submission_is_throttled(self):
        payload = {"name": "Alex", "email": "alex@example.com", "consent": "on"}
        self.client.post(reverse("store:preorders"), payload)
        response = self.client.post(reverse("store:preorders"), payload)
        self.assertContains(response, "Please wait a minute")
        self.assertEqual(Inquiry.objects.count(), 1)

    @override_settings(STORE_FEATURES_ENABLED=False)
    def test_showcase_blocks_data_collection(self):
        for route in ("preorders", "wholesale"):
            self.assertNotContains(
                self.client.get(reverse(f"store:{route}")), '<form method="post"'
            )
            response = self.client.post(
                reverse(f"store:{route}"),
                {
                    "name": "Alex",
                    "email": "alex@example.com",
                    "consent": "on",
                    "business_name": "Example",
                },
            )
            self.assertEqual(response.status_code, 403)
        self.assertFalse(Inquiry.objects.exists())

    def test_forms_require_csrf(self):
        response = Client(enforce_csrf_checks=True).post(reverse("store:preorders"), {})
        self.assertEqual(response.status_code, 403)

    def test_empty_kids_and_preorders_have_honest_empty_states(self):
        Product.objects.all().delete()
        self.assertContains(
            self.client.get(reverse("store:kids")), "Something little is on the way"
        )
        self.assertContains(
            self.client.get(reverse("store:preorders")), "No preorder releases announced yet"
        )


class ClothingAssetTests(TestCase):
    def test_existing_demo_art_resolves_from_collection_folders(self):
        from django.contrib.staticfiles import finders

        for slug, product, color in (
            ("demo-most-sacred", "most-sacred-tee", "ivory"),
            ("demo-walk-in-faith", "walk-in-faith-tee", "charcoal"),
            ("demo-abide", "abide-tee", "stone"),
        ):
            item = Product(slug=slug, is_demo=True)
            source = finders.find(item.placeholder_art)
            self.assertIsNotNone(source)
            self.assertTrue(
                str(source).endswith(f"clothing/faith-edit/{product}/images/{color}/front.svg")
            )

    def test_private_plans_are_not_static_assets(self):
        from django.contrib.staticfiles import finders

        self.assertIsNone(finders.find("clothing/kids/star-and-halo-tee/product.json"))
        self.assertIsNone(finders.find("clothing/faith-edit/most-sacred-tee/README.md"))
