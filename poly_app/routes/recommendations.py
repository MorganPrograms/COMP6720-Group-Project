# poly_app/routes/recommendations.py
from flask import Blueprint, jsonify, g, request
from bson import ObjectId
from datetime import date

from poly_app.utils.jwt_tools import jwt_required
from poly_app.db_neo4j import cypher_read
from poly_app.db_mongo import get_mongo_db
from poly_app.db_mysql import query_one

recommend_bp = Blueprint("recommendations", __name__)

db = get_mongo_db()
books_col = db["books"]


def _book_to_json(book):
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
        "file_id": book.get("file_id"),
        "mime_type": book.get("mime_type", "application/pdf"),
    }


def _get_user_age_and_country(user_id: int):
    row = query_one(
        """
        SELECT country, date_of_birth
        FROM user_profile
        WHERE user_id = %s
        """,
        (user_id,),
    )
    if not row:
        return None, None

    country = row.get("country")
    dob = row.get("date_of_birth")

    age = None
    if dob:
        today = date.today()
        age = today.year - dob.year - (
            (today.month, today.day) < (dob.month, dob.day)
        )
    return age, country


def _filter_by_age_and_premium(books, user_status, age):
    filtered = []
    for b in books:
        age_rating = int(b.get("age_rating", 0) or 0)
        if age is not None and age < age_rating:
            continue
        if b.get("premium_only") and user_status != "PREMIUM":
            continue
        filtered.append(b)
    return filtered


@recommend_bp.get("/books")
@jwt_required
def recommend_books():
    """
    Returns a list of recommended books for the current user.

    Priority:
    1. Collaborative: similar users based on READ edges
    2. Content-based: genre/tag/language overlap
    3. Fallback: popular by views
    """
    user = g.user
    user_id = user["id"]
    status = user["status"]

    limit = request.args.get("limit", 10)
    try:
        limit = int(limit)
    except ValueError:
        limit = 10
    if limit <= 0:
        limit = 10

    age, country = _get_user_age_and_country(user_id)

    # -------- 1) Collaborative filtering in Neo4j --------
    collab = cypher_read(
        """
        MATCH (u:User {user_id: $uid})-[:READ]->(b:Book)<-[:READ]-(other:User)-[:READ]->(rec:Book)
        WHERE other.user_id <> $uid
          AND NOT EXISTS( (u)-[:READ]->(rec) )
        RETURN rec.book_id AS book_id, count(*) AS score
        ORDER BY score DESC
        LIMIT $limit
        """,
        {"uid": str(user_id), "limit": limit},
    )

    book_ids = [row["book_id"] for row in collab]

    # -------- 2) Content-based fallback --------
    if not book_ids:
        content = cypher_read(
            """
            MATCH (u:User {user_id: $uid})-[:READ]->(b:Book)
            MATCH (b)-[:HAS_GENRE|HAS_TAG|IN_LANGUAGE]->(t)<-[:HAS_GENRE|HAS_TAG|IN_LANGUAGE]-(rec:Book)
            WHERE NOT EXISTS( (u)-[:READ]->(rec) )
            RETURN rec.book_id AS book_id, count(*) AS score
            ORDER BY score DESC
            LIMIT $limit
            """,
            {"uid": str(user_id), "limit": limit},
        )
        book_ids = [row["book_id"] for row in content]

    # -------- 3) MongoDB fallback: popular by views --------
    books = []
    if book_ids:
        # Load from Mongo
        oids = []
        for bid in book_ids:
            try:
                oids.append(ObjectId(bid))
            except Exception:
                continue
        if oids:
            cursor = books_col.find({"_id": {"$in": oids}})
            books = list(cursor)
    else:
        cursor = books_col.find().sort("views", -1).limit(limit)
        books = list(cursor)

    # Apply age + premium filters
    books = _filter_by_age_and_premium(books, status, age)

    return jsonify([_book_to_json(b) for b in books])
