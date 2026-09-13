"""Shared image-processing logic for product photos (issue #33), used by
both the profile-facing upload route and the admin one - resizing/encoding
shouldn't be duplicated just because two different auth gates call it.
"""

import os

from PIL import Image, UnidentifiedImageError

# issue #33: "~100-128px, ~2-5KB" - long side capped at 128px, WebP quality
# tuned to land in that size range for a typical product photo.
MAX_DIMENSION = 128
QUALITY = 65


def save(image_dir, product_id, file):
    """Resizes an uploaded photo to a small thumbnail and stores it as
    WebP keyed by product id (not barcode - see repositories/products.py).
    Returns the path written. Raises ValueError if the upload isn't a
    real image."""
    try:
        image = Image.open(file.stream)
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
