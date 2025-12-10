# poly_app/routes/auth.py
from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

from poly_app.db_mysql import query_one, execute
from poly_app.utils.jwt_tools import create_token
from poly_app.utils.validation import (
    validate_email,
    validate_password,
    validate_username,
    parse_date_yyyy_mm_dd,
)

auth_bp = Blueprint("auth", __name__)


def _public_user_from_row(row: dict) -> dict:
    return {
        "id": row["id"],
        "email": row["email"],
        "status": row["status"],
        "total_spent": float(row["total_spent"] or 0),
        "total_books_read": int(row["total_books_read"] or 0),
    }


@auth_bp.post("/register")
def register():
    """
    JSON body:
    {
      "email": "...",
      "password": "...",
      "username": "...",
      "country": "...",
      "date_of_birth": "YYYY-MM-DD"
    }
    Creates FREE user + profile, returns JWT + user.
    """
    data = request.get_json(silent=True) or {}

    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    username = (data.get("username") or "").strip()
    country = (data.get("country") or "").strip()
    dob_str = (data.get("date_of_birth") or "").strip()

    if not validate_email(email):
        return jsonify({"error": "Invalid email format"}), 400
    if not validate_password(password, min_length=6):
        return jsonify({"error": "Password must be at least 6 characters"}), 400
    if not validate_username(username):
        return jsonify({"error": "Username must be 3–32 chars, letters/numbers/_/-"}), 400

    dob = parse_date_yyyy_mm_dd(dob_str)
    if not dob:
        return jsonify({"error": "date_of_birth must be YYYY-MM-DD"}), 400

    # Ensure email and username are unique
    existing_email = query_one(
        "SELECT id FROM users WHERE email = %s",
        (email,),
    )
    if existing_email:
        return jsonify({"error": "Email already registered"}), 400

    existing_username = query_one(
        "SELECT user_id FROM user_profile WHERE username = %s",
        (username,),
    )
    if existing_username:
        return jsonify({"error": "Username already taken"}), 400

    pwd_hash = generate_password_hash(password)

    # Insert user (FREE by default), then profile
    user_id = execute(
        """
        INSERT INTO users (email, password_hash, status, total_spent, total_books_read)
        VALUES (%s, %s, 'FREE', 0.00, 0)
        """,
        (email, pwd_hash),
    )

    execute(
        """
        INSERT INTO user_profile (user_id, username, country, date_of_birth)
        VALUES (%s, %s, %s, %s)
        """,
        (user_id, username, country, dob),
    )

    user_row = query_one(
        "SELECT id, email, status, total_spent, total_books_read FROM users WHERE id = %s",
        (user_id,),
    )

    token = create_token(user_row)
    return (
        jsonify(
            {
                "token": token,
                "user": _public_user_from_row(user_row),
            }
        ),
        201,
    )


@auth_bp.post("/login")
def login():
    """
    JSON body:
    {
      "email": "...",
      "password": "..."
    }
    Returns JWT + public user info.
    """
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    user = query_one(
        "SELECT * FROM users WHERE email = %s",
        (email,),
    )
    if not user:
        return jsonify({"error": "Invalid credentials"}), 401

    if not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Invalid credentials"}), 401

    token = create_token(user)
    public_user = _public_user_from_row(user)

    return jsonify({"token": token, "user": public_user})
