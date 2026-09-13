import re

from flask import Blueprint, current_app, jsonify, request

from admin_auth import require_admin
from db import get_db
from repositories import products as products_repo
from repositories import profiles as profiles_repo

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")

PIN_PATTERN = re.compile(r"^\d{4}$")
BARCODE_MAX_LENGTH = 64
NAME_MAX_LENGTH = 200
CATEGORY_MAX_LENGTH = 100


@admin_bp.get("/profiles")
@require_admin
def list_profiles():
    conn = get_db(current_app.config["DATABASE_PATH"])
    return jsonify(profiles_repo.get_all_admin(conn))


@admin_bp.post("/profiles/<int:profile_id>/reset-pin")
@require_admin
def reset_pin(profile_id):
    data = request.get_json(force=True)
    pin = data.get("pin") or ""
    if not PIN_PATTERN.match(pin):
        return jsonify({"error": "pin must be exactly 4 digits"}), 400

    conn = get_db(current_app.config["DATABASE_PATH"])
    if profiles_repo.get_by_id(conn, profile_id) is None:
        return jsonify({"error": "not found"}), 404

    profiles_repo.reset_pin(conn, profile_id, pin)
    return "", 204


@admin_bp.post("/profiles/<int:profile_id>/clear-lockout")
@require_admin
def clear_lockout(profile_id):
    conn = get_db(current_app.config["DATABASE_PATH"])
    if profiles_repo.get_by_id(conn, profile_id) is None:
        return jsonify({"error": "not found"}), 404

    profiles_repo.clear_lockout(conn, profile_id)
    return "", 204


@admin_bp.delete("/profiles/<int:profile_id>")
@require_admin
def delete_profile(profile_id):
    conn = get_db(current_app.config["DATABASE_PATH"])
    if profiles_repo.get_by_id(conn, profile_id) is None:
        return jsonify({"error": "not found"}), 404

    profiles_repo.delete(conn, profile_id)
    return "", 204


@admin_bp.get("/products")
@require_admin
def list_products():
    conn = get_db(current_app.config["DATABASE_PATH"])
    return jsonify(products_repo.get_all(conn))


@admin_bp.patch("/products/<int:product_id>")
@require_admin
def update_product(product_id):
    data = request.get_json(force=True)
    conn = get_db(current_app.config["DATABASE_PATH"])
    if products_repo.get_by_id(conn, product_id) is None:
        return jsonify({"error": "not found"}), 404

    barcode = data.get("barcode")
    name = data.get("name")
    category = data.get("category")
    if barcode is not None:
        barcode = barcode.strip()
        if not barcode or len(barcode) > BARCODE_MAX_LENGTH:
            return jsonify({"error": f"barcode must be 1-{BARCODE_MAX_LENGTH} characters"}), 400
    if name is not None:
        name = name.strip()
        if not name or len(name) > NAME_MAX_LENGTH:
            return jsonify({"error": f"name must be 1-{NAME_MAX_LENGTH} characters"}), 400
        if "<" in name or ">" in name:
            return jsonify({"error": "name cannot contain '<' or '>'"}), 400
    if category is not None:
        category = category.strip() or None
        if category and len(category) > CATEGORY_MAX_LENGTH:
            return jsonify({"error": f"category must be {CATEGORY_MAX_LENGTH} characters or fewer"}), 400
        if category and ("<" in category or ">" in category):
            return jsonify({"error": "category cannot contain '<' or '>'"}), 400

    product = products_repo.update(conn, product_id, barcode=barcode, name=name, category=category)
    return jsonify(product)


@admin_bp.delete("/products/<int:product_id>")
@require_admin
def delete_product(product_id):
    conn = get_db(current_app.config["DATABASE_PATH"])
    if products_repo.get_by_id(conn, product_id) is None:
        return jsonify({"error": "not found"}), 404

    products_repo.delete(conn, product_id)
    return "", 204
