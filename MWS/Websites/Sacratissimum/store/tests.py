from decimal import Decimal
from io import BytesIO, StringIO
from tempfile import TemporaryDirectory

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from .models import Product, ProductImage, ProductVariant


class StorefrontTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.product = Product.objects.create(name="A real sample", slug="sample", description="A thoughtful design.", price=Decimal("29.95"), is_published=True, is_featured=True)
        cls.draft = Product.objects.create(name="Private draft", slug="draft", description="Hidden", price=Decimal("30"))
        ProductVariant.objects.create(product=cls.product, size="M", color="Ivory")
        ProductVariant.objects.create(product=cls.product, size="XL", color="Secret color", is_active=False)

    def test_public_pages_and_navigation(self):
        for name in ("home", "collection", "story"):
            with self.subTest(name=name):
                response = self.client.get(reverse(f"store:{name}"))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'id="main"')
                self.assertContains(response, 'aria-controls="site-nav"')
                self.assertContains(response, reverse("store:collection"))

    def test_only_published_products_are_visible(self):
        for route in ("home", "collection"):
            response = self.client.get(reverse(f"store:{route}"))
            self.assertContains(response, "A real sample")
            self.assertNotContains(response, "Private draft")
        self.assertEqual(self.client.get(self.draft.get_absolute_url()).status_code, 404)
        self.assertEqual(self.client.get(reverse("store:product", args=["missing"])).status_code, 404)

    def test_detail_has_money_variants_and_placeholder(self):
        response = self.client.get(self.product.get_absolute_url())
        self.assertContains(response, "$29.95")
        self.assertContains(response, "Ivory")
        self.assertContains(response, "Size M")
        self.assertNotContains(response, "Secret color")
        self.assertContains(response, "tee-placeholder.svg")
        self.assertContains(response, "Preview only")
        self.assertContains(response, "Online purchasing is not available")
        self.assertNotContains(response, "Add to cart")

    def test_home_falls_back_to_published_collection(self):
        self.product.is_featured = False
        self.product.save()
        self.assertContains(self.client.get(reverse("store:home")), "A real sample")

    def test_featured_drafts_stay_hidden(self):
        self.draft.is_featured = True
        self.draft.save()
        self.assertNotContains(self.client.get(reverse("store:home")), "Private draft")

    def test_empty_states(self):
        Product.objects.update(is_published=False)
        for route in ("home", "collection"):
            response = self.client.get(reverse(f"store:{route}"))
            self.assertContains(response, "The collection is taking shape.")
            self.assertContains(response, reverse("store:story"))

    def test_demo_label_and_price(self):
        self.product.is_demo = True
        self.product.save()
        response = self.client.get(self.product.get_absolute_url())
        self.assertContains(response, "Fictional merchandise and illustrative pricing")
        self.assertContains(self.client.get(reverse("store:collection")), "Demo concept")

    def test_descriptions_are_escaped(self):
        self.product.description = '<script>alert("x")</script>'
        self.product.save()
        response = self.client.get(self.product.get_absolute_url())
        self.assertNotContains(response, '<script>alert("x")</script>')
        self.assertContains(response, "&lt;script&gt;")

    def test_collection_search_color_and_sort(self):
        other = Product.objects.create(name="Another design", slug="other", description="A cross design", price=Decimal("19.00"), is_published=True)
        ProductVariant.objects.create(product=other, size="S", color="Charcoal")
        route = reverse("store:collection")
        response = self.client.get(route, {"q": "cross"})
        self.assertContains(response, "Another design")
        self.assertNotContains(response, "A real sample")
        response = self.client.get(route, {"color": "Ivory"})
        self.assertContains(response, "A real sample")
        self.assertNotContains(response, "Another design")
        response = self.client.get(route, {"sort": "price-low"})
        self.assertEqual(list(response.context["products"]), [other, self.product])
        response = self.client.get(route, {"sort": "price-high"})
        self.assertEqual(list(response.context["products"]), [self.product, other])

    def test_collection_no_matches_and_safe_parameters(self):
        route = reverse("store:collection")
        self.assertContains(self.client.get(route, {"q": "no-such-product"}), "No pieces match just yet.")
        self.assertEqual(self.client.get(route, {"sort": "invalid"}).status_code, 200)
        self.assertContains(self.client.get(route, {"q": '<script>alert(1)</script>'}), "&lt;script&gt;")
        response = self.client.get(route, {"color": "Secret color"})
        self.assertEqual(list(response.context["products"]), [])
        self.assertNotIn("Secret color", response.context["colors"])

    def test_concept_art_does_not_replace_real_photography(self):
        self.product.slug = "demo-most-sacred"
        self.assertTrue(self.product.placeholder_art.endswith("tee-placeholder.svg"))
        self.product.is_demo = True
        self.assertTrue(self.product.placeholder_art.endswith("concept-sacred.svg"))

    def test_price_validation(self):
        self.product.price = Decimal("-1")
        with self.assertRaises(ValidationError):
            self.product.full_clean()

    def test_unique_variant(self):
        duplicate = ProductVariant(product=self.product, size="M", color="Ivory")
        with self.assertRaises(ValidationError):
            duplicate.full_clean()

    def test_gallery_and_uploaded_images(self):
        with TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=directory):
            image = BytesIO()
            Image.new("RGB", (10, 10), "white").save(image, format="PNG")
            for index in range(2):
                ProductImage.objects.create(product=self.product, image=SimpleUploadedFile(f"tee-{index}.png", image.getvalue(), content_type="image/png"), alt_text=f"Ivory tee view {index}", display_order=index)
            response = self.client.get(self.product.get_absolute_url())
            self.assertContains(response, "data-gallery-src=", count=2)
            self.assertContains(response, 'alt="Ivory tee view 0"')
            self.assertNotContains(response, "tee-placeholder.svg")

    def test_admin_requires_login(self):
        response = self.client.get(reverse("admin:store_product_changelist"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response.url)

    def test_admin_product_management(self):
        from django.contrib.auth import get_user_model
        owner = get_user_model().objects.create_superuser("owner", "owner@example.test", "test-only-password")
        self.client.force_login(owner)
        response = self.client.get(reverse("admin:store_product_change", args=[self.product.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Website visibility")
        self.assertContains(response, 'name="images-TOTAL_FORMS"')
        self.assertContains(response, 'name="variants-TOTAL_FORMS"')

    def test_pages_use_bounded_queries(self):
        with self.assertNumQueries(4):
            response = self.client.get(reverse("store:collection"))
            self.assertEqual(response.status_code, 200)


class DemoCommandTests(TestCase):
    def test_demo_is_unpublished_by_default_and_repeatable(self):
        call_command("load_demo_products", stdout=StringIO())
        self.assertEqual(Product.objects.count(), 3)
        self.assertFalse(Product.objects.filter(is_published=True).exists())
        self.assertTrue(all(p.is_demo for p in Product.objects.all()))
        self.assertEqual(ProductVariant.objects.count(), 15)
        first = Product.objects.first()
        first.name = "Owner edited"
        first.save()
        call_command("load_demo_products", publish=True, stdout=StringIO())
        first.refresh_from_db()
        self.assertEqual(first.name, "Owner edited")
        self.assertFalse(first.is_published)
        self.assertEqual(Product.objects.count(), 3)

    def test_explicitly_published_demo_is_labeled(self):
        call_command("load_demo_products", publish=True, stdout=StringIO())
        self.assertEqual(Product.objects.filter(is_published=True, is_demo=True).count(), 3)
        self.assertContains(self.client.get(reverse("store:collection")), "Demo concept", count=3)
