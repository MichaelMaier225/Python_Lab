import time

from django.conf import settings
from django.contrib import messages
from django.db.models import Prefetch, Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import InquiryForm
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


def kids(request):
    return render(
        request,
        "store/kids.html",
        {
            "products": published_products().filter(audience=Product.Audience.KIDS),
        },
    )


def inquiries(request, kind):
    enabled = settings.STORE_FEATURES_ENABLED
    form = InquiryForm(request.POST if request.method == "POST" else None, kind=kind)
    if request.method == "POST":
        if not enabled:
            return render(
                request,
                "store/inquiry.html",
                {
                    "kind": kind,
                    "inquiries_enabled": False,
                    "form": form,
                    "products": published_products().filter(preorder_interest=True, is_demo=False),
                },
                status=403,
            )
        if request.session.get("last_inquiry_at", 0) > time.time() - 60:
            form.add_error(None, "Please wait a minute before sending another inquiry.")
        elif form.is_valid():
            form.save()
            request.session["last_inquiry_at"] = time.time()
            messages.success(
                request, "Your inquiry was received. No order or payment has been placed."
            )
            return redirect("store:" + ("preorders" if kind == "preorder" else "wholesale"))
    return render(
        request,
        "store/inquiry.html",
        {
            "kind": kind,
            "form": form,
            "inquiries_enabled": enabled,
            "products": published_products().filter(preorder_interest=True, is_demo=False),
        },
    )
