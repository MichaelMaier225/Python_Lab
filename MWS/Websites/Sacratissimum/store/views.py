from django.db.models import Prefetch, Q
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
    products = published_products()
    query = request.GET.get("q", "").strip()[:100]
    color = request.GET.get("color", "").strip()[:60]
    sort = request.GET.get("sort", "featured")
    ordering = {
        "featured": ("display_order", "name", "pk"),
        "name": ("name", "pk"),
        "price-low": ("price", "name", "pk"),
        "price-high": ("-price", "name", "pk"),
    }
    if sort not in ordering:
        sort = "featured"
    if query:
        products = products.filter(Q(name__icontains=query) | Q(description__icontains=query))
    if color:
        products = products.filter(variants__is_active=True, variants__color=color).distinct()
    colors = (
        ProductVariant.objects.filter(product__is_published=True, is_active=True)
        .order_by("color")
        .values_list("color", flat=True)
        .distinct()
    )
    return render(
        request,
        "store/collection.html",
        {
            "products": products.order_by(*ordering[sort]),
            "colors": colors,
            "query": query,
            "selected_color": color,
            "selected_sort": sort,
        },
    )


def product(request, slug):
    item = get_object_or_404(published_products(), slug=slug)
    related = published_products().exclude(pk=item.pk)[:3]
    return render(request, "store/product.html", {"product": item, "related": related})


def story(request):
    return render(request, "store/story.html")
