from django.conf import settings

from .payments import checkout_ready


def shop(request):
    cart = request.session.get("cart", {}) if settings.STORE_FEATURES_ENABLED else {}
    count = (
        sum(min(20, int(q)) for q in cart.values() if str(q).isdigit())
        if isinstance(cart, dict)
        else 0
    )
    return {
        "store_features": settings.STORE_FEATURES_ENABLED,
        "bag_count": count,
        "store_checkout_ready": checkout_ready(),
    }
