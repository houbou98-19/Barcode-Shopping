import json
import urllib.error
import urllib.parse
import urllib.request

from flask import Blueprint, current_app, jsonify, request

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
