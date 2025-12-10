# poly_app/utils/jwt_tools.py
import os
import datetime
from functools import wraps

import jwt
from flask import request, g, jsonify

from poly_app.db_mysql import query_one

JWT_SECRET = os.getenv("JWT_SECRET", "supersecretkey")
JWT_ALG = "HS256"
JWT_EXP_HOURS = int(os.getenv("JWT_EXP_HOURS", 8))


def create_token(user_row: dict) -> str:
    """
    Create a JWT for a given user record.
    Expects keys: id, email, status
    """
    payload = {
        "sub": user_row["id"],
        "email": user_row["email"],
        "status": user_row["status"],
        "iat": datetime.datetime.utcnow(),
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=JWT_EXP_HOURS),
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)
    # PyJWT >= 2 returns str; older might return bytes
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    return token


def decode_token(token: str) -> dict:
    """
    Decode a JWT and return the payload or raise jwt exceptions.
    """
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])


def _load_user_from_payload(payload: dict):
    """
    Load a user from MySQL given a decoded payload.
    """
    user_id = payload.get("sub")
    if not user_id:
        return None

    user = query_one(
        """
        SELECT u.id,
               u.email,
               u.status,
               u.total_spent,
               u.total_books_read
        FROM users u
        WHERE u.id = %s
        """,
        (user_id,),
    )
    return user


def jwt_required(fn):
    """
    Decorator for API routes.
    - Reads Authorization: Bearer <token>
    - Verifies and decodes JWT
    - Loads user into flask.g.user
    - Returns 401/403 on invalid/missing token
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid Authorization header"}), 401

        token = auth_header.split(" ", 1)[1].strip()
        if not token:
            return jsonify({"error": "Missing token"}), 401

        try:
            payload = decode_token(token)
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401

        user = _load_user_from_payload(payload)
        if not user:
            return jsonify({"error": "User not found"}), 404

        g.user = user
        return fn(*args, **kwargs)
    return wrapper
