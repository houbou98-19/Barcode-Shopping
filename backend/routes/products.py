import json
import os
import urllib.error
import urllib.parse
import urllib.request

from flask import Blueprint, current_app, jsonify, request, send_file

import product_images
import settings_store
from db import get_db
from extensions import limiter
from repositories import products as products_repo
from session_auth import require_session

products_bp = Blueprint("products", __name__, url_prefix="/api/products")

BARCODE_MAX_LENGTH = 64
NAME_MAX_LENGTH = 200
CATEGORY_MAX_LENGTH = 100

OFF_LOOKUP_URL = "https://world.openfoodfacts.org/api/v2/product/{barcode}.json?fields=product_name,categories_tags"
OFF_LOOKUP_TIMEOUT_SECONDS = 3


@products_bp.get("")
def list_products():
    conn = get_db(current_app.config["DATABASE_PATH"])
    return jsonify(products_repo.get_all(conn))


@products_bp.post("")
@limiter.limit("20/minute")
@require_session
def create_product():
    data = request.get_json(force=True)
    barcode = (data.get("barcode") or "").strip()
    name = (data.get("name") or "").strip()
    category = (data.get("category") or "").strip() or None
    if not barcode or not name:
        return jsonify({"error": "barcode and name are required"}), 400
    if len(barcode) > BARCODE_MAX_LENGTH:
        return jsonify({"error": f"barcode must be {BARCODE_MAX_LENGTH} characters or fewer"}), 400
    if len(name) > NAME_MAX_LENGTH:
        return jsonify({"error": f"name must be {NAME_MAX_LENGTH} characters or fewer"}), 400
    if category and len(category) > CATEGORY_MAX_LENGTH:
        return jsonify({"error": f"category must be {CATEGORY_MAX_LENGTH} characters or fewer"}), 400
    if "<" in name or ">" in name or (category and ("<" in category or ">" in category)):
        return jsonify({"error": "name and category cannot contain '<' or '>'"}), 400

    conn = get_db(current_app.config["DATABASE_PATH"])
    product = products_repo.create(conn, barcode, name, category)
    return jsonify(product), 201


@products_bp.get("/<int:product_id>")
def get_product(product_id):
    conn = get_db(current_app.config["DATABASE_PATH"])
    product = products_repo.get_by_id(conn, product_id)
    if product is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(product)


@products_bp.get("/barcode/<barcode>")
def get_products_by_barcode(barcode):
    """Returns a list, not a single product - the same barcode can
    legitimately match more than one product (see repositories/products.py)."""
    conn = get_db(current_app.config["DATABASE_PATH"])
    return jsonify(products_repo.get_by_barcode(conn, barcode))


@products_bp.get("/lookup/<barcode>")
@limiter.limit("20/minute")
def lookup_product(barcode):
    """Live per-scan lookup against Open Food Facts for a barcode not found
    locally (issue #44) - never touches the database, just hands back a
    name/category to prefill the manual-entry form with. Opt-in via the
    off_lookup_enabled setting, toggled from /admin - off by default, and
    when it's off or the lookup fails for any reason, this responds as
    "nothing found" rather than an error, since manual entry always works
    as the fallback either way."""
    not_found = jsonify({"available": False}), 200
    if not settings_store.get_bool("off_lookup_enabled", default=False):
        return not_found

    url = OFF_LOOKUP_URL.format(barcode=urllib.parse.quote(barcode, safe=""))
    try:
        with urllib.request.urlopen(url, timeout=OFF_LOOKUP_TIMEOUT_SECONDS) as response:
            payload = json.load(response)
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        return not_found

    if payload.get("status") != 1:
        return not_found

    product = payload.get("product") or {}
    name = (product.get("product_name") or "").strip()
    if not name:
        return not_found

    # Open Food Facts categories are most-general-first (e.g.
    # "en:snacks", "en:sweet-snacks", "en:biscuits") - the last tag is the
    # most specific, closest match to this app's single free-text category.
    categories = product.get("categories_tags") or []
    category = None
    if categories:
        category = categories[-1].split(":")[-1].replace("-", " ").title()

    return jsonify(
        {
            "available": True,
            "name": name[:NAME_MAX_LENGTH],
            "category": category[:CATEGORY_MAX_LENGTH] if category else None,
        }
    )


@products_bp.post("/<int:product_id>/image")
@limiter.limit("20/minute")
@require_session
def upload_product_image(product_id):
    """Accepts a user photo (camera or gallery - issue #33), resizes it to
    a small thumbnail, and stores it as WebP keyed by product id (not
    barcode, since barcode isn't unique - see repositories/products.py)."""
    conn = get_db(current_app.config["DATABASE_PATH"])
    if products_repo.get_by_id(conn, product_id) is None:
        return jsonify({"error": "not found"}), 404

    file = request.files.get("image")
    if file is None or file.filename == "":
        return jsonify({"error": "image file is required"}), 400

    try:
        image_path = product_images.save(current_app.config["IMAGE_DIR"], product_id, file)
    except ValueError:
        return jsonify({"error": "not a valid image"}), 400

    product = products_repo.update(conn, product_id, image_path=image_path)
    return jsonify(product)


@products_bp.get("/<int:product_id>/image")
def get_product_image(product_id):
    """image_path is an internal server-side path, never returned as-is by
    the API (issue #33) - the frontend always points <img> at this
    deterministic URL instead and falls back to a placeholder on 404."""
    conn = get_db(current_app.config["DATABASE_PATH"])
    product = products_repo.get_by_id(conn, product_id)
    image_path = product.get("image_path") if product else None
    if not image_path or not os.path.isfile(image_path):
        return jsonify({"error": "not found"}), 404

    return send_file(image_path, mimetype="image/webp")
