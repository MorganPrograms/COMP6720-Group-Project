# poly_app/routes/comments.py
from flask import Blueprint, request, jsonify, g
from bson import ObjectId

from poly_app.utils.jwt_tools import jwt_required
from poly_app.db_mysql import query_all, query_one, execute
from poly_app.db_mongo import get_mongo_db

comments_bp = Blueprint("comments", __name__)

db = get_mongo_db()
books_col = db["books"]


def _load_book(book_id):
    try:
        return books_col.find_one({"_id": ObjectId(book_id)})
    except Exception:
        return None


@comments_bp.get("/<book_id>")
@jwt_required
def list_comments(book_id):
    """Return comments for a book."""
    book = _load_book(book_id)
    if not book:
        return jsonify({"error": "Book not found"}), 404

    rows = query_all(
        """
        SELECT c.id,
               c.user_id,
               p.username,
               c.content,
               c.created_at
        FROM comments c
        JOIN user_profile p ON p.user_id = c.user_id
        WHERE mongo_book_id = %s
        ORDER BY c.created_at DESC
        """,
        (book_id,),
    )

    return jsonify(rows)


@comments_bp.post("/<book_id>")
@jwt_required
def add_comment(book_id):
    data = request.get_json(silent=True) or {}
    if not data and request.form:
        data = request.form
    content = (data.get("content") or "").strip()
    """
    JSON body:
    {
        "content": "..."
    }

    Must not be empty.
    """
    data = request.get_json(silent=True) or {}
    content = (data.get("content") or "").strip()

    if not content:
        return jsonify({"error": "Comment cannot be empty"}), 400

    book = _load_book(book_id)
    if not book:
        return jsonify({"error": "Book not found"}), 404

    user_id = g.user["id"]

    execute(
        """
        INSERT INTO comments (user_id, mongo_book_id, content)
        VALUES (%s, %s, %s)
        """,
        (user_id, book_id, content),
    )

    return jsonify({"message": "Comment added"}), 201


@comments_bp.delete("/delete/<comment_id>")
@jwt_required
def delete_comment(comment_id):
    """
    Deletes a comment.
    In Phase 4.5, admin_required() will be applied here.
    """
    row = query_one(
        "SELECT id FROM comments WHERE id = %s",
        (comment_id,),
    )

    if not row:
        return jsonify({"error": "Comment not found"}), 404

    # Admin validation will be wrapped around this later
    execute("DELETE FROM comments WHERE id = %s", (comment_id,))

    return jsonify({"message": "Comment deleted"})
