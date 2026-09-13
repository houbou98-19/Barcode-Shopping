"""Shared image-processing logic for product photos (issue #33), used by
both the profile-facing upload route and the admin one - resizing/encoding
shouldn't be duplicated just because two different auth gates call it.
"""

import os

from PIL import Image, UnidentifiedImageError

# Bumped past issue #33's original "~100-128px" suggestion after testing
# on a real phone screen - a much bigger source resolution makes the
# lightbox view (App.vue/ProductCard.vue) look sharp instead of blurry,
# while WebP compression at this quality keeps a 1000-product catalog
# nowhere near a size worth worrying about (see plan.md discussion).
MAX_DIMENSION = 1000
QUALITY = 65


def save(image_dir, product_id, stream):
    """Resizes a photo (an uploaded file's .stream, or any other readable
    binary stream - e.g. a downloaded Open Food Facts image, see issue
    #58) to a small thumbnail and stores it as WebP keyed by product id
    (not barcode - see repositories/products.py). Returns the path
    written. Raises ValueError if it isn't a real image."""
    try:
        image = Image.open(stream)
        image.load()
    except (UnidentifiedImageError, OSError, ValueError):
        raise ValueError("not a valid image")

    if image.mode not in ("RGB", "L"):
        # Flatten transparency onto white first - converting straight to
        # RGB would otherwise composite it onto black.
        rgba = image.convert("RGBA")
        flattened = Image.new("RGB", rgba.size, (255, 255, 255))
        flattened.paste(rgba, mask=rgba.split()[-1])
        image = flattened

    image.thumbnail((MAX_DIMENSION, MAX_DIMENSION))

    image_path = os.path.join(image_dir, f"{product_id}.webp")
    image.save(image_path, "WEBP", quality=QUALITY)
    return image_path


def delete(image_path):
    if image_path and os.path.isfile(image_path):
        os.remove(image_path)
