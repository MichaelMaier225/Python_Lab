from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, render
from .models import Product, ProductVariant


def published_products():
    return Product.objects.filter(is_published=True).prefetch_related(
        "images", Prefetch("variants", queryset=ProductVariant.objects.filter(is_active=True))
    )


def home(request):
    available = published_products()
    featured = available.filter(is_featured=True)
    products = (featured if featured.exists() else available)[:3]
    return render(request, "store/home.html", {"products": products})


def collection(request):
    return render(request, "store/collection.html", {"products": published_products()})


def product(request, slug):
    item = get_object_or_404(published_products(), slug=slug)
    related = published_products().exclude(pk=item.pk)[:3]
    return render(request, "store/product.html", {"product": item, "related": related})


def story(request):
    return render(request, "store/story.html")
