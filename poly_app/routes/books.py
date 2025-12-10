# poly_app/routes/books.py
from flask import Blueprint, jsonify, request, g
from bson import ObjectId

from poly_app.db_mongo import get_mongo_db
from poly_app.utils.jwt_tools import jwt_required

books_bp = Blueprint("books", __name__)
db = get_mongo_db()
books_col = db["books"]


def _book_to_json(book):
    """Convert MongoDB book document to JSON-safe dict."""
    return {
        "id": str(book["_id"]),
        "title": book["title"],
        "author": book.get("author"),
        "price": float(book.get("price", 0)),
        "genres": book.get("genres", []),
        "tags": book.get("tags", []),
        "languages": book.get("languages", []),
        "premium_only": book.get("premium_only", False),
        "age_rating": book.get("age_rating", 0),
        "rating": book.get("rating", {"avg": 0, "count": 0}),
        "views": book.get("views", 0),
        "cover_url": book.get("cover_url"),
        "file_id": book.get("file_id"),   # For Google Drive reader
        "mime_type": book.get("mime_type", "application/pdf"),
    }


@books_bp.get("/")
@jwt_required
def list_books():
    """
    Returns all books.
    Supports filtering by:
    - genre
    - tag
    - language
    - premium_only
    """
    user = g.user
    filters = {}

    genre = request.args.get("genre")
    tag = request.args.get("tag")
    language = request.args.get("language")
    premium_only = request.args.get("premium_only")

    if genre:
        filters["genres"] = genre
    if tag:
        filters["tags"] = tag
    if language:
        filters["languages"] = language
    if premium_only:
        filters["premium_only"] = premium_only.lower() == "true"

    cursor = books_col.find(filters)
    results = []

    for book in cursor:
        # Hide premium-only books from FREE users
        if book.get("premium_only") and user["status"] != "PREMIUM":
            continue
        results.append(_book_to_json(book))

    return jsonify(results)


@books_bp.get("/<book_id>")
@jwt_required
def get_book(book_id):
    """
    Get a single book by ID.
    FREE users cannot see premium-only content details.
    """
    try:
        oid = ObjectId(book_id)
    except:
        return jsonify({"error": "Invalid book ID"}), 400

    book = books_col.find_one({"_id": oid})
    if not book:
        return jsonify({"error": "Book not found"}), 404

    user = g.user

    # Restrict premium-only visibility
    if book.get("premium_only") and user["status"] != "PREMIUM":
        return jsonify({"error": "Premium users only"}), 403

    return jsonify(_book_to_json(book))


@books_bp.get("/search")
@jwt_required
def search_books():
    """
    Simple search by title or author.
    """
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify([])

    cursor = books_col.find(
        {
            "$or": [
                {"title": {"$regex": q, "$options": "i"}},
                {"author": {"$regex": q, "$options": "i"}},
            ]
        }
    )

    results = [_book_to_json(book) for book in cursor]
    return jsonify(results)
