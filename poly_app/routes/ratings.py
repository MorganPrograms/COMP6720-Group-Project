# poly_app/routes/ratings.py
from flask import Blueprint, request, jsonify, g
from bson import ObjectId

from poly_app.utils.jwt_tools import jwt_required
from poly_app.utils.validation import validate_rating
from poly_app.db_mysql import query_one, execute
from poly_app.db_mongo import get_mongo_db
from poly_app.db_neo4j import cypher_write

ratings_bp = Blueprint("ratings", __name__)

db = get_mongo_db()
books_col = db["books"]


def _load_book(book_id):
    try:
        return books_col.find_one({"_id": ObjectId(book_id)})
    except Exception:
        return None


@ratings_bp.post("/<book_id>")
@jwt_required
def rate_book(book_id):
    data = request.get_json(silent=True) or {}
    if not data and request.form:
        data = request.form
    raw_rating = data.get("rating")

    """
    JSON body:
    {
        "rating": 1–5
    }

    Conditions:
    - User must have purchased OR rented the book
    - User may only rate once
    - MongoDB rating.avg and rating.count updated
    - MySQL logs rating
    - Neo4j updates :RATED edge
    """
    data = request.get_json(silent=True) or {}
    raw_rating = data.get("rating")

    if not validate_rating(raw_rating):
        return jsonify({"error": "Rating must be an integer 1–5"}), 400

    rating = int(raw_rating)
    user_id = g.user["id"]

    # Load book
    book = _load_book(book_id)
    if not book:
        return jsonify({"error": "Book not found"}), 404

    # Ensure user purchased or rented it
    purchased = query_one(
        """
        SELECT id FROM purchases
        WHERE user_id = %s AND mongo_book_id = %s
        LIMIT 1
        """,
        (user_id, book_id),
    )
    if not purchased:
        return jsonify({"error": "You must buy or rent this book before rating it"}), 403

    # Ensure user has not rated it before
    already_rated = query_one(
        """
        SELECT id FROM ratings
        WHERE user_id = %s AND mongo_book_id = %s
        LIMIT 1
        """,
        (user_id, book_id),
    )
    if already_rated:
        return jsonify({"error": "You have already rated this book"}), 400

    # Write rating to MySQL
    execute(
        """
        INSERT INTO ratings (user_id, mongo_book_id, rating)
        VALUES (%s, %s, %s)
        """,
        (user_id, book_id, rating),
    )

    # Update MongoDB rating object
    old_rating = book.get("rating", {"avg": 0, "count": 0})
    old_avg = float(old_rating.get("avg", 0))
    old_count = int(old_rating.get("count", 0))

    new_count = old_count + 1
    new_avg = round(((old_avg * old_count) + rating) / new_count, 2)

    books_col.update_one(
        {"_id": book["_id"]},
        {"$set": {"rating.avg": new_avg, "rating.count": new_count}},
    )

    # Neo4j reinforcement
    cypher_write(
        """
        MERGE (u:User {user_id: $uid})
        MERGE (b:Book {book_id: $bid})
        MERGE (u)-[:RATED {value: $rating}]->(b)
        """,
        {"uid": str(user_id), "bid": str(book["_id"]), "rating": rating},
    )

    return jsonify({"message": "Rating submitted", "avg": new_avg, "count": new_count})
