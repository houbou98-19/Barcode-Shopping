import re

from flask import Blueprint, current_app, jsonify, request

from db import get_db
from extensions import limiter
from repositories import profiles as profiles_repo
from repositories import sessions as sessions_repo

auth_bp = Blueprint("auth", __name__, url_prefix="/api/profiles")

NAME_MAX_LENGTH = 50
PIN_PATTERN = re.compile(r"^\d{4}$")


@auth_bp.get("")
def list_profiles():
    conn = get_db(current_app.config["DATABASE_PATH"])
    return jsonify(profiles_repo.get_all(conn))


@auth_bp.post("")
@limiter.limit("20/minute")
def create_profile():
    data = request.get_json(force=True)
    name = (data.get("name") or "").strip()
    pin = data.get("pin") or ""
    if not name or not pin:
        return jsonify({"error": "name and pin are required"}), 400
    if len(name) > NAME_MAX_LENGTH:
        return jsonify({"error": f"name must be {NAME_MAX_LENGTH} characters or fewer"}), 400
    if not PIN_PATTERN.match(pin):
        return jsonify({"error": "pin must be exactly 4 digits"}), 400

    conn = get_db(current_app.config["DATABASE_PATH"])
    if profiles_repo.name_exists(conn, name):
        return jsonify({"error": "a profile with that name already exists"}), 400

    profile = profiles_repo.create(conn, name, pin)
    return jsonify(profile), 201


@auth_bp.post("/<int:profile_id>/verify-pin")
@limiter.limit("10/minute")
def verify_pin(profile_id):
    data = request.get_json(force=True)
    pin = data.get("pin") or ""

    conn = get_db(current_app.config["DATABASE_PATH"])
    if not profiles_repo.verify_pin(conn, profile_id, pin):
        # Same error for "wrong pin" and "locked" - don't hand a
        # brute-forcer information about lockout state.
        return jsonify({"error": "invalid pin"}), 401

    session = sessions_repo.create(conn, profile_id)
    return jsonify(session)
