from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from store.models import Product, ProductVariant


class Command(BaseCommand):
    help = "Create labeled fictional product concepts as drafts. Use --publish to explicitly display them."

    def add_arguments(self, parser):
        parser.add_argument("--publish", action="store_true", help="Publish clearly labeled demo concepts to the showcase.")

    @transaction.atomic
    def handle(self, *args, **options):
        concepts = [
            ("demo-most-sacred", "The Most Sacred Tee", "32.00", "Warm ivory",
             "A concept centered on the meaning of our name: most sacred. Quiet lettering gives a simple T-shirt a thoughtful focus.\n\nThis is fictional demo merchandise. Fabric, fit, care and final design are not yet specified."),
            ("demo-walk-in-faith", "The Walk in Faith Tee", "34.00", "Charcoal",
             "A concept inspired by the everyday practice of faith. An understated expression for the ordinary moments that shape a life.\n\nThis is fictional demo merchandise. The illustration is a generic placeholder, not a rendering of this design. Materials and fit are to be confirmed."),
            ("demo-abide", "The Abide Tee", "32.00", "Stone",
             "A concept built around a single word: abide. A reminder to stay rooted in faith, wherever the day leads.\n\nThis is fictional demo merchandise. The illustration is a generic placeholder, not a rendering of this design. Final product details are not yet available."),
        ]
        for order, (slug, name, price, color, description) in enumerate(concepts):
            existing = Product.objects.filter(slug=slug).first()
            if existing:
                self.stdout.write(f"Skipped existing product: {slug} (no owner edits changed).")
                continue
            product = Product.objects.create(
                slug=slug, name=name, price=Decimal(price), description=description,
                is_demo=True, is_featured=True, is_published=options["publish"],
                availability=Product.Availability.PREVIEW, display_order=order,
            )
            ProductVariant.objects.bulk_create([
                ProductVariant(product=product, color=color, size=size, display_order=i)
                for i, size in enumerate(["S", "M", "L", "XL", "2XL"])
            ])
        self.stdout.write(self.style.SUCCESS(
            "Demo content processed. Existing records were preserved. "
            "New concepts are labeled fictional and " + ("published." if options["publish"] else "saved as unpublished drafts. Publish them explicitly in admin when desired.")
        ))
