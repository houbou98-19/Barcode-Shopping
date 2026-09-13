from flask import Blueprint, current_app, g, jsonify, request

from db import get_db
from events import broadcast
from extensions import limiter
from repositories import lists as lists_repo
from repositories import shopping_list as shopping_list_repo
from session_auth import require_session

lists_bp = Blueprint("lists", __name__, url_prefix="/api/lists")

NAME_MAX_LENGTH = 100


@lists_bp.get("")
@require_session
def list_lists():
    conn = get_db(current_app.config["DATABASE_PATH"])
    return jsonify(lists_repo.get_for_profile(conn, g.profile_id))


@lists_bp.post("")
@limiter.limit("20/minute")
@require_session
def create_list():
    data = request.get_json(force=True)
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400
    if len(name) > NAME_MAX_LENGTH:
        return jsonify({"error": f"name must be {NAME_MAX_LENGTH} characters or fewer"}), 400
    if "<" in name or ">" in name:
        return jsonify({"error": "name cannot contain '<' or '>'"}), 400

    conn = get_db(current_app.config["DATABASE_PATH"])
    new_list = lists_repo.create_shared(conn, g.profile_id, name)
    return jsonify(new_list), 201


@lists_bp.post("/join")
@limiter.limit("20/minute")
@require_session
def join_list():
    data = request.get_json(force=True)
    code = (data.get("join_code") or "").strip()

    conn = get_db(current_app.config["DATABASE_PATH"])
    joined = lists_repo.join(conn, g.profile_id, code)
    if joined is None:
        return jsonify({"error": "invalid join code"}), 404
    return jsonify(joined)


@lists_bp.post("/<int:list_id>/leave")
@require_session
def leave_list(list_id):
    conn = get_db(current_app.config["DATABASE_PATH"])
    target = lists_repo.get_by_id(conn, list_id)
    if target is None or not lists_repo.is_member(conn, list_id, g.profile_id):
        return jsonify({"error": "not found"}), 404
    if target["is_personal"]:
        return jsonify({"error": "can't leave your own personal list"}), 400

    lists_repo.leave(conn, list_id, g.profile_id)
    lists_repo.delete_if_orphaned(conn, list_id)
    return "", 204


@lists_bp.delete("/<int:list_id>")
@require_session
def delete_list(list_id):
    conn = get_db(current_app.config["DATABASE_PATH"])
    target = lists_repo.get_by_id(conn, list_id)
    if target is None or not lists_repo.is_member(conn, list_id, g.profile_id):
        return jsonify({"error": "not found"}), 404
    if target["is_personal"]:
        return jsonify({"error": "can't delete your own personal list"}), 400
    if target["created_by_profile_id"] != g.profile_id:
        return jsonify({"error": "only the creator can delete this list"}), 403

    lists_repo.delete(conn, list_id)
    broadcast("list_updated")
    return "", 204


@lists_bp.get("/<int:list_id>/items")
@require_session
def list_items(list_id):
    conn = get_db(current_app.config["DATABASE_PATH"])
    if not lists_repo.is_member(conn, list_id, g.profile_id):
        return jsonify({"error": "not found"}), 404

    return jsonify(shopping_list_repo.get_all(conn, list_id))


@lists_bp.post("/<int:list_id>/items")
@limiter.limit("30/minute")
@require_session
def add_item(list_id):
    conn = get_db(current_app.config["DATABASE_PATH"])
    if not lists_repo.is_member(conn, list_id, g.profile_id):
        return jsonify({"error": "not found"}), 404

    data = request.get_json(force=True)
    product_id = data.get("product_id")
    quantity = data.get("quantity", 1)
    if not product_id:
        return jsonify({"error": "product_id is required"}), 400
    if not shopping_list_repo.product_exists(conn, product_id):
        return jsonify({"error": "unknown product_id"}), 400

    item = shopping_list_repo.create(conn, product_id, quantity, list_id, g.profile_id)
    broadcast("list_updated")
    return jsonify(item), 201


@lists_bp.post("/<int:target_list_id>/items/move")
@limiter.limit("30/minute")
@require_session
def move_items(target_list_id):
    conn = get_db(current_app.config["DATABASE_PATH"])
    if not lists_repo.is_member(conn, target_list_id, g.profile_id):
        return jsonify({"error": "not found"}), 404

    data = request.get_json(force=True)
    item_ids = data.get("item_ids") or []
    if not item_ids:
        return jsonify({"error": "item_ids is required"}), 400

    # Every item must exist and belong to a list the requester is also a
    # member of - can't move an item you don't have access to in the
    # first place, regardless of where it's headed.
    for item_id in item_ids:
        existing = shopping_list_repo.get_by_id(conn, item_id)
        if existing is None or not lists_repo.is_member(conn, existing["list_id"], g.profile_id):
            return jsonify({"error": "not found"}), 404

    shopping_list_repo.move_items(conn, item_ids, target_list_id)
    broadcast("list_updated")
    return "", 204


@lists_bp.patch("/<int:list_id>/items/<int:item_id>")
@limiter.limit("120/minute")
@require_session
def update_item(list_id, item_id):
    conn = get_db(current_app.config["DATABASE_PATH"])
    if not lists_repo.is_member(conn, list_id, g.profile_id):
        return jsonify({"error": "not found"}), 404

    data = request.get_json(force=True)
    if "quantity" not in data and "checked" not in data:
        return jsonify({"error": "nothing to update"}), 400

    existing = shopping_list_repo.get_by_id(conn, item_id)
    # Same 404 whether the item doesn't exist or belongs to a different
    # list - doesn't leak that a given id belongs to another list.
    if existing is None or existing["list_id"] != list_id:
        return jsonify({"error": "not found"}), 404

    item = shopping_list_repo.update(
        conn,
        item_id,
        quantity=data.get("quantity"),
        checked=data.get("checked"),
    )
    broadcast("list_updated")
    return jsonify(item)


@lists_bp.delete("/<int:list_id>/items/<int:item_id>")
@limiter.limit("60/minute")
@require_session
def delete_item(list_id, item_id):
    conn = get_db(current_app.config["DATABASE_PATH"])
    if not lists_repo.is_member(conn, list_id, g.profile_id):
        return jsonify({"error": "not found"}), 404

    existing = shopping_list_repo.get_by_id(conn, item_id)
    if existing is None or existing["list_id"] != list_id:
        return jsonify({"error": "not found"}), 404

    shopping_list_repo.delete(conn, item_id)
    broadcast("list_updated")
    return "", 204
