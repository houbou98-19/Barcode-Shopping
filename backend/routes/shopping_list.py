from flask import Blueprint, current_app, g, jsonify, request

from db import get_db
from events import broadcast
from extensions import limiter
from repositories import shopping_list as shopping_list_repo
from session_auth import require_session

shopping_list_bp = Blueprint("shopping_list", __name__, url_prefix="/api/list")


@shopping_list_bp.get("")
@require_session
def list_items():
    conn = get_db(current_app.config["DATABASE_PATH"])
    return jsonify(shopping_list_repo.get_all(conn, g.profile_id))


@shopping_list_bp.post("")
@limiter.limit("30/minute")
@require_session
def add_item():
    data = request.get_json(force=True)
    product_id = data.get("product_id")
    quantity = data.get("quantity", 1)
    if not product_id:
        return jsonify({"error": "product_id is required"}), 400

    conn = get_db(current_app.config["DATABASE_PATH"])
    if not shopping_list_repo.product_exists(conn, product_id):
        return jsonify({"error": "unknown product_id"}), 400

    item = shopping_list_repo.create(conn, product_id, quantity, g.profile_id)
    broadcast("list_updated")
    return jsonify(item), 201


@shopping_list_bp.patch("/<int:item_id>")
@limiter.limit("120/minute")
@require_session
def update_item(item_id):
    data = request.get_json(force=True)
    if "quantity" not in data and "checked" not in data:
        return jsonify({"error": "nothing to update"}), 400

    conn = get_db(current_app.config["DATABASE_PATH"])
    existing = shopping_list_repo.get_by_id(conn, item_id)
    # Same 404 whether the item doesn't exist or belongs to another
    # profile - doesn't leak that a given id belongs to someone else.
    if existing is None or existing["profile_id"] != g.profile_id:
        return jsonify({"error": "not found"}), 404

    item = shopping_list_repo.update(
        conn,
        item_id,
        quantity=data.get("quantity"),
        checked=data.get("checked"),
    )
    broadcast("list_updated")
    return jsonify(item)


@shopping_list_bp.delete("/<int:item_id>")
@limiter.limit("60/minute")
@require_session
def delete_item(item_id):
    conn = get_db(current_app.config["DATABASE_PATH"])
    existing = shopping_list_repo.get_by_id(conn, item_id)
    if existing is None or existing["profile_id"] != g.profile_id:
        return jsonify({"error": "not found"}), 404

    shopping_list_repo.delete(conn, item_id)
    broadcast("list_updated")
    return "", 204
