# poly_app/routes/profile.py
from flask import Blueprint, jsonify, request, g
from werkzeug.security import generate_password_hash

from poly_app.utils.jwt_tools import jwt_required
from poly_app.utils.validation import (
    validate_email,
    validate_password,
    validate_username,
    parse_date_yyyy_mm_dd,
)
from poly_app.db_mysql import query_one, execute
from poly_app.db_neo4j import cypher_write

profile_bp = Blueprint("profile", __name__)


def _load_full_profile(user_id: int) -> dict | None:
    return query_one(
        """
        SELECT u.id,
               u.email,
               u.status,
               u.total_spent,
               u.total_books_read,
               p.username,
               p.country,
               p.date_of_birth
        FROM users u
        JOIN user_profile p ON p.user_id = u.id
        WHERE u.id = %s
        """,
        (user_id,),
    )


@profile_bp.get("/me")
@jwt_required
def me():
    """
    Returns combined user + profile info for the JWT-authenticated user.
    """
    user_id = g.user["id"]
    profile = _load_full_profile(user_id)
    if not profile:
        return jsonify({"error": "Profile not found"}), 404
    return jsonify(profile)


@profile_bp.put("/update")
@jwt_required
def update_profile():
    """
    JSON body (all optional, but at least one must be present):
    {
      "email": "...",
      "password": "...",
      "username": "...",
      "country": "...",
      "date_of_birth": "YYYY-MM-DD"
    }
    Enforces validation, updates users + user_profile.
    """
    data = request.get_json(silent=True) or {}
    user_id = g.user["id"]

    new_email = data.get("email")
    new_password = data.get("password")
    new_username = data.get("username")
    new_country = data.get("country")
    new_dob_str = data.get("date_of_birth")

    # Track updates separately for each table
    user_updates = []
    user_params = []

    profile_updates = []
    profile_params = []

    # Email
    if new_email is not None:
        email = new_email.strip().lower()
        if not validate_email(email):
            return jsonify({"error": "Invalid email format"}), 400

        # Ensure uniqueness
        existing = query_one(
            "SELECT id FROM users WHERE email = %s AND id <> %s",
            (email, user_id),
        )
        if existing:
            return jsonify({"error": "Email already in use"}), 400

        user_updates.append("email = %s")
        user_params.append(email)

    # Password
    if new_password:
        if not validate_password(new_password, min_length=6):
            return jsonify({"error": "Password must be at least 6 characters"}), 400
        pwd_hash = generate_password_hash(new_password)
        user_updates.append("password_hash = %s")
        user_params.append(pwd_hash)

    # Username
    if new_username is not None:
        username = new_username.strip()
        if not validate_username(username):
            return jsonify({"error": "Invalid username format"}), 400

        existing_un = query_one(
            "SELECT user_id FROM user_profile WHERE username = %s AND user_id <> %s",
            (username, user_id),
        )
        if existing_un:
            return jsonify({"error": "Username already taken"}), 400

        profile_updates.append("username = %s")
        profile_params.append(username)

    # Country
    if new_country is not None:
        profile_updates.append("country = %s")
        profile_params.append(new_country.strip())

    # DOB
    if new_dob_str is not None:
        dob = parse_date_yyyy_mm_dd(new_dob_str)
        if not dob:
            return jsonify({"error": "date_of_birth must be YYYY-MM-DD"}), 400
        profile_updates.append("date_of_birth = %s")
        profile_params.append(dob)

    if not user_updates and not profile_updates:
        return jsonify({"error": "No fields to update"}), 400

    # Apply user table updates
    if user_updates:
        sql = "UPDATE users SET " + ", ".join(user_updates) + " WHERE id = %s"
        user_params.append(user_id)
        execute(sql, tuple(user_params))

    # Apply user_profile updates
    if profile_updates:
        sql = "UPDATE user_profile SET " + ", ".join(profile_updates) + " WHERE user_id = %s"
        profile_params.append(user_id)
        execute(sql, tuple(profile_params))

    updated = _load_full_profile(user_id)
    return jsonify({"message": "Profile updated", "profile": updated})


@profile_bp.post("/upgrade")
@jwt_required
def upgrade_to_premium():
    """
    Upgrades FREE user to PREMIUM.
    - Adds a 'UPGRADE' row in purchases
    - Increments total_spent
    - Updates Neo4j user status
    """
    user_id = g.user["id"]
    current_status = g.user["status"]

    if current_status == "PREMIUM":
        return jsonify({"error": "User already PREMIUM"}), 400

    # You can later make this dynamic / from config
    upgrade_price = 9.99

    # Update MySQL user status and total_spent
    execute(
        """
        UPDATE users
        SET status = 'PREMIUM',
            total_spent = total_spent + %s
        WHERE id = %s
        """,
        (upgrade_price, user_id),
    )

    # Log the upgrade in purchases table (mongo_book_id stores a marker)
    execute(
        """
        INSERT INTO purchases (user_id, mongo_book_id, purchase_type, amount)
        VALUES (%s, %s, %s, %s)
        """,
        (user_id, "PREMIUM_UPGRADE", "UPGRADE", upgrade_price),
    )

    # Update Neo4j user node
    cypher_write(
        """
        MERGE (u:User {user_id: $uid})
        SET u.status = 'PREMIUM'
        """,
        {"uid": str(user_id)},
    )

    updated = _load_full_profile(user_id)
    return jsonify({"message": "Upgraded to PREMIUM", "profile": updated})
