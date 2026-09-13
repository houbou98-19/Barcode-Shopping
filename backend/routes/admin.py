import re

from flask import Blueprint, current_app, jsonify, request

import product_images
import settings_store
from admin_auth import require_admin
from db import get_db
from repositories import lists as lists_repo
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


@admin_bp.get("/lists")
@require_admin
def list_lists():
    conn = get_db(current_app.config["DATABASE_PATH"])
    return jsonify(lists_repo.get_all_admin(conn))


@admin_bp.delete("/lists/<int:list_id>")
@require_admin
def delete_list(list_id):
    conn = get_db(current_app.config["DATABASE_PATH"])
    if lists_repo.get_by_id(conn, list_id) is None:
        return jsonify({"error": "not found"}), 404

    lists_repo.delete(conn, list_id)
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
    product = products_repo.get_by_id(conn, product_id)
    if product is None:
        return jsonify({"error": "not found"}), 404

    products_repo.delete(conn, product_id)
    # Moderating a bad product entry should also clean up its thumbnail
    # (issue #33), not leave an orphaned file behind - same spirit as
    # products_repo.delete() cascading its shopping_list_items.
    product_images.delete(product.get("image_path"))
    return "", 204


@admin_bp.post("/products/<int:product_id>/image")
@require_admin
def upload_product_image(product_id):
    """Lets an admin replace or add a product's photo directly - e.g. to
    fix a bad or offensive user-submitted image without deleting and
    recreating the whole product. Same processing as the profile-facing
    upload (see product_images.py), just gated by the admin password
    instead of a profile session."""
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


@admin_bp.get("/settings")
@require_admin
def get_settings():
    return jsonify({"off_lookup_enabled": settings_store.get_bool("off_lookup_enabled", default=False)})


@admin_bp.patch("/settings")
@require_admin
def update_settings():
    data = request.get_json(force=True)
    if "off_lookup_enabled" not in data:
        return jsonify({"error": "off_lookup_enabled is required"}), 400

    enabled = bool(data["off_lookup_enabled"])
    settings_store.set_bool("off_lookup_enabled", enabled)
    return jsonify({"off_lookup_enabled": enabled})
