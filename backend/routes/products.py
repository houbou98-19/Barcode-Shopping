from flask import Blueprint, current_app, jsonify, request

from db import get_db
from extensions import limiter
from repositories import products as products_repo
from session_auth import require_session

products_bp = Blueprint("products", __name__, url_prefix="/api/products")

BARCODE_MAX_LENGTH = 64
NAME_MAX_LENGTH = 200
CATEGORY_MAX_LENGTH = 100


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
