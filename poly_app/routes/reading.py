# poly_app/routes/reading.py
from flask import Blueprint, jsonify, g
from bson import ObjectId

from poly_app.utils.jwt_tools import jwt_required
from poly_app.db_mysql import query_one, execute_transaction
from poly_app.db_mongo import get_mongo_db
from poly_app.db_neo4j import cypher_write

reading_bp = Blueprint("reading", __name__)

db = get_mongo_db()
books_col = db["books"]


def _load_book(book_id: str):
    try:
        oid = ObjectId(book_id)
    except Exception:
        return None
    return books_col.find_one({"_id": oid})


def _check_age_and_premium(user: dict, book: dict):
    user_age = user.get("age", 30)
    required_age = int(book.get("age_rating", 0) or 0)
    if user_age < required_age:
        return False, "User does not meet age requirement for this book."

    if book.get("premium_only") and user["status"] != "PREMIUM":
        return False, "This book is available to PREMIUM users only."

    return True, None


@reading_bp.post("/<book_id>")
@jwt_required
def mark_read(book_id):
    """
    Records that the user read a book.

    Flow:
    - Ensure the book exists in MongoDB
    - Ensure user has either BUY or RENT record in MySQL
    - Enforce age + premium restrictions
    - Increment books.views in MongoDB
    - Increment users.total_books_read in MySQL
    - Create (User)-[:READ]->(Book) in Neo4j
    """
    user = g.user
    user_id = user["id"]

    book = _load_book(book_id)
    if not book:
        return jsonify({"error": "Book not found"}), 404

    ok, msg = _check_age_and_premium(user, book)
    if not ok:
        return jsonify({"error": msg}), 403

    # Check for a prior purchase or rental
    purchase = query_one(
        """
        SELECT id, purchase_type
        FROM purchases
        WHERE user_id = %s
          AND mongo_book_id = %s
        LIMIT 1
        """,
        (user_id, book_id),
    )

    if not purchase:
        return jsonify({"error": "You must BUY or RENT this book before reading it"}), 403

    # ACID block: increment total_books_read and keep counters consistent
    ops = [
        (
            """
            UPDATE users
            SET total_books_read = total_books_read + 1
            WHERE id = %s
            """,
            (user_id,),
        )
    ]

    execute_transaction(ops)

    # MongoDB: increment views
    books_col.update_one(
        {"_id": book["_id"]},
        {"$inc": {"views": 1}},
    )

    # Neo4j: connect user to book via READ relationship
    cypher_write(
        """
        MERGE (u:User {user_id: $uid})
        MERGE (b:Book {book_id: $bid})
        MERGE (u)-[r:READ]->(b)
        ON CREATE SET r.count = 1
        ON MATCH SET r.count = coalesce(r.count, 0) + 1
        """,
        {"uid": str(user_id), "bid": str(book["_id"])},
    )

    return jsonify(
        {
            "message": "Read recorded",
            "purchase_type": purchase["purchase_type"],
        }
    )
