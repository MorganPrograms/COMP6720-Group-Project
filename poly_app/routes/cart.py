# poly_app/routes/cart.py
from flask import Blueprint, jsonify, request, g
from bson import ObjectId

from poly_app.db_redis import get_redis
from poly_app.db_mongo import get_mongo_db
from poly_app.utils.jwt_tools import jwt_required

cart_bp = Blueprint("cart", __name__)

redis_client = get_redis()
db = get_mongo_db()
books_col = db["books"]


def _load_book(book_id):
    """Finds a book by ObjectId. Returns None if invalid."""
    try:
        oid = ObjectId(book_id)
    except:
        return None
    return books_col.find_one({"_id": oid})


def _book_to_cart_item(book, quantity):
    return {
        "id": str(book["_id"]),
        "title": book["title"],
        "price": float(book.get("price", 0)),
        "quantity": quantity,
        "premium_only": book.get("premium_only", False),
        "age_rating": book.get("age_rating", 0),
        "cover_url": book.get("cover_url"),
    }


@cart_bp.get("/")
@jwt_required
def view_cart():
    """Return all cart items for the user."""
    user_id = g.user["id"]
    key = f"cart:{user_id}"

    raw_cart = redis_client.hgetall(key)
    items = []

    for book_id, qty in raw_cart.items():
        book = _load_book(book_id)
        if book:
            items.append(_book_to_cart_item(book, int(qty)))

    return jsonify(items)


@cart_bp.post("/add")
@jwt_required
def add_to_cart():
    """
    JSON:
    {
      "book_id": "...",
      "quantity": 1
    }
    """
    data = request.get_json(silent=True) or {}
    book_id = data.get("book_id")
    qty = int(data.get("quantity", 1))

    user = g.user
    user_id = user["id"]

    if not book_id:
        return jsonify({"error": "book_id required"}), 400

    book = _load_book(book_id)
    if not book:
        return jsonify({"error": "Book not found"}), 404

    # Age restriction check — user must be old enough
    age_rating = book.get("age_rating", 0)
    user_age = user.get("age", 30)  # Will be injected later from DOB
    if user_age < age_rating:
        return jsonify({"error": "This book cannot be purchased due to age restrictions"}), 403

    # Premium-only book check (cannot add if not premium)
    if book.get("premium_only") and user["status"] != "PREMIUM":
        return jsonify({"error": "Premium users only"}), 403

    key = f"cart:{user_id}"
    redis_client.hincrby(key, book_id, qty)

    return jsonify({"message": "Added to cart"})


@cart_bp.post("/remove")
@jwt_required
def remove_item():
    """
    JSON:
    {
      "book_id": "..."
    }
    """
    data = request.get_json(silent=True) or {}
    book_id = data.get("book_id")

    if not book_id:
        return jsonify({"error": "book_id required"}), 400

    user_id = g.user["id"]
    key = f"cart:{user_id}"

    redis_client.hdel(key, book_id)

    return jsonify({"message": "Removed"})


@cart_bp.post("/clear")
@jwt_required
def clear_cart():
    """Clears all cart items for the user."""
    user_id = g.user["id"]
    key = f"cart:{user_id}"
    redis_client.delete(key)
    return jsonify({"message": "Cart cleared"})
