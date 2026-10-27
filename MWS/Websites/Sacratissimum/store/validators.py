from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError


def product_image_size(value):
    if value.size > 5 * 1024 * 1024:
        raise ValidationError("Product images must be 5 MB or smaller.")
    try:
        value.open("rb")
        image = Image.open(value)
        if image.width * image.height > 16_000_000:
            raise ValidationError("Product images must be 16 megapixels or smaller.")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise ValidationError("Upload a valid, reasonably sized product image.")
    finally:
        try:
            value.seek(0)
        except (OSError, ValueError):
            pass
