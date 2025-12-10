# poly_app/routes/purchases.py
from flask import Blueprint, jsonify, request, g
from bson import ObjectId

from poly_app.utils.jwt_tools import jwt_required
from poly_app.db_mysql import query_all, execute_transaction
from poly_app.db_mongo import get_mongo_db
from poly_app.db_neo4j import cypher_write

purchases_bp = Blueprint("purchases", __name__)

db = get_mongo_db()
books_col = db["books"]


def _load_book(book_id: str):
    """Fetch a MongoDB book by ID, or None if invalid/missing."""
    try:
        oid = ObjectId(book_id)
    except Exception:
        return None
    return books_col.find_one({"_id": oid})


@purchases_bp.get("/")
@jwt_required
def list_purchases():
    """
    List all purchases for the current user.
    This is purely MySQL, but conceptually references MongoDB book IDs.
    """
    user_id = g.user["id"]
    rows = query_all(
        """
        SELECT id,
               mongo_book_id,
               purchase_type,
               amount,
               created_at
        FROM purchases
        WHERE user_id = %s
        ORDER BY created_at DESC
        """,
        (user_id,),
    )
    return jsonify(rows)


def _check_age_and_premium(user: dict, book: dict):
    """
    Enforce age_rating and premium_only rules.
    Age logic can be enhanced later using date_of_birth from user_profile.
    """
    # Age: default to a safe adult age if not computed yet
    user_age = user.get("age", 30)
    required_age = int(book.get("age_rating", 0) or 0)
    if user_age < required_age:
        return False, "User does not meet age requirement for this book."

    # Premium-only: only PREMIUM users can purchase these
    if book.get("premium_only") and user["status"] != "PREMIUM":
        return False, "This book is available to PREMIUM users only."

    return True, None


@purchases_bp.post("/buy")
@jwt_required
def buy_book():
    data = request.get_json(silent=True) or {}
    if not data and request.form:
        data = request.form
    book_id = data.get("book_id")
    """
    JSON:
    {
      "book_id": "..."
    }

    - Loads book from MongoDB
    - Validates age + premium constraints
    - Inserts into purchases
    - Increments users.total_spent
    - Records Neo4j (u)-[:BOUGHT]->(b)
    """
    data = request.get_json(silent=True) or {}
    book_id = data.get("book_id")

    if not book_id:
        return jsonify({"error": "book_id is required"}), 400

    book = _load_book(book_id)
    if not book:
        return jsonify({"error": "Book not found"}), 404

    ok, msg = _check_age_and_premium(g.user, book)
    if not ok:
        return jsonify({"error": msg}), 403

    price = float(book.get("price", 0))
    user_id = g.user["id"]

    ops = [
        (
            """
            INSERT INTO purchases (user_id, mongo_book_id, purchase_type, amount)
            VALUES (%s, %s, 'BUY', %s)
            """,
            (user_id, str(book["_id"]), price),
        ),
        (
            """
            UPDATE users
            SET total_spent = total_spent + %s
            WHERE id = %s
            """,
            (price, user_id),
        ),
    ]

    execute_transaction(ops)

    # Neo4j: record purchase
    cypher_write(
        """
        MERGE (u:User {user_id: $uid})
        MERGE (b:Book {book_id: $bid})
        MERGE (u)-[:BOUGHT]->(b)
        """,
        {"uid": str(user_id), "bid": str(book["_id"])},
    )

    return jsonify({"message": "Book purchased successfully", "amount": price})

@purchases_bp.post("/rent")
@jwt_required
def rent_book():
    data = request.get_json(silent=True) or {}
    if not data and request.form:
        data = request.form
    book_id = data.get("book_id")
    """
    JSON:
    {
      "book_id": "..."
    }

    - Same checks as buy
    - purchase_type = 'RENT'
    - Amount is a fraction of full price (e.g. 40%)
    """
    data = request.get_json(silent=True) or {}
    book_id = data.get("book_id")

    if not book_id:
        return jsonify({"error": "book_id is required"}), 400

    book = _load_book(book_id)
    if not book:
        return jsonify({"error": "Book not found"}), 404

    ok, msg = _check_age_and_premium(g.user, book)
    if not ok:
        return jsonify({"error": msg}), 403

    full_price = float(book.get("price", 0))
    rent_price = round(full_price * 0.4, 2)
    user_id = g.user["id"]

    ops = [
        (
            """
            INSERT INTO purchases (user_id, mongo_book_id, purchase_type, amount)
            VALUES (%s, %s, 'RENT', %s)
            """,
            (user_id, str(book["_id"]), rent_price),
        ),
        (
            """
            UPDATE users
            SET total_spent = total_spent + %s
            WHERE id = %s
            """,
            (rent_price, user_id),
        ),
    ]

    execute_transaction(ops)

    # Neo4j: record rental as a relationship
    cypher_write(
        """
        MERGE (u:User {user_id: $uid})
        MERGE (b:Book {book_id: $bid})
        MERGE (u)-[:RENTED]->(b)
        """,
        {"uid": str(user_id), "bid": str(book["_id"])},
    )

    return jsonify({"message": "Book rented successfully", "amount": rent_price})
