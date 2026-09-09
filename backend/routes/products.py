from flask import Blueprint, current_app, jsonify, request

from db import get_db
from repositories import products as products_repo

products_bp = Blueprint("products", __name__, url_prefix="/api/products")


@products_bp.get("")
def list_products():
    conn = get_db(current_app.config["DATABASE_PATH"])
    return jsonify(products_repo.get_all(conn))


@products_bp.post("")
def create_product():
    data = request.get_json(force=True)
    barcode = data.get("barcode")
    name = data.get("name")
    category = data.get("category")
    if not barcode or not name:
        return jsonify({"error": "barcode and name are required"}), 400

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
