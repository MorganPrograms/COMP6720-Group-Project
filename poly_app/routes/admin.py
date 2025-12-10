# poly_app/routes/admin.py
from flask import Blueprint, jsonify, g
from functools import wraps

from poly_app.utils.jwt_tools import jwt_required
from poly_app.utils.ui_auth import ADMIN_USER_IDS
from poly_app.db_mysql import query_one, query_all
from poly_app.db_mongo import get_mongo_db

admin_bp = Blueprint("admin", __name__)

db = get_mongo_db()
books_col = db["books"]


def admin_api_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user_id = g.user["id"]
        if user_id not in ADMIN_USER_IDS:
            return jsonify({"error": "Admin access required"}), 403
        return fn(*args, **kwargs)
    return wrapper


@admin_bp.get("/overview")
@jwt_required
@admin_api_required
def overview():
    """
    Returns summary statistics for the admin dashboard:
    - total users
    - total premium users
    - total purchases
    - total revenue
    - total books (Mongo)
    """
    total_users_row = query_one("SELECT COUNT(*) AS c FROM users")
    total_premium_row = query_one(
        "SELECT COUNT(*) AS c FROM users WHERE status = 'PREMIUM'"
    )
    purchases_row = query_one(
        "SELECT COUNT(*) AS c, COALESCE(SUM(amount), 0) AS revenue FROM purchases"
    )

    total_books = books_col.count_documents({})

    return jsonify(
        {
            "total_users": total_users_row["c"],
            "total_premium": total_premium_row["c"],
            "total_purchases": purchases_row["c"],
            "total_revenue": float(purchases_row["revenue"]),
            "total_books": total_books,
        }
    )


@admin_bp.get("/users")
@jwt_required
@admin_api_required
def users():
    """
    Lists all users with key fields.
    """
    rows = query_all(
        """
        SELECT u.id,
               u.email,
               u.status,
               u.total_spent,
               u.total_books_read,
               p.username,
               p.country
        FROM users u
        JOIN user_profile p ON p.user_id = u.id
        ORDER BY u.id ASC
        """
    )
    # Convert decimals/None
    for r in rows:
        r["total_spent"] = float(r["total_spent"] or 0)
        r["total_books_read"] = int(r["total_books_read"] or 0)
    return jsonify(rows)


@admin_bp.get("/books/popular")
@jwt_required
@admin_api_required
def popular_books():
    """
    Top 20 books by views from MongoDB.
    """
    cursor = books_col.find().sort("views", -1).limit(20)
    books = []
    for b in cursor:
        books.append(
            {
                "id": str(b["_id"]),
                "title": b["title"],
                "author": b.get("author"),
                "views": int(b.get("views", 0)),
                "rating": b.get("rating", {"avg": 0, "count": 0}),
                "premium_only": b.get("premium_only", False),
            }
        )
    return jsonify(books)
