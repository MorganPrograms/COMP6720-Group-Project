# poly_app/routes/ui.py
from poly_app.db_neo4j import cypher_read

from poly_app.db_neo4j import track_book_interaction

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
)
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date
from bson import ObjectId

from poly_app.db_mysql import query_one, query_all, execute
from poly_app.db_mongo import get_mongo_db
from poly_app.db_redis import get_redis
from poly_app.utils.validation import (
    validate_email,
    validate_password,
    validate_username,
    parse_date_yyyy_mm_dd,
)
from poly_app.utils.ui_auth import (
    get_current_user,
    login_required,
    admin_required,
    ADMIN_USER_IDS,
)

ui_bp = Blueprint("ui", __name__, template_folder="../../templates")

db = get_mongo_db()
books_col = db["books"]
redis_client = get_redis()


# ------------------------------
# Helper
# ------------------------------
def _compute_age(dob):
    if not dob:
        return None
    today = date.today()
    return today.year - dob.year - (
        (today.month, today.day) < (dob.month, dob.day)
    )


@ui_bp.app_context_processor
def inject_globals():
    """Provide current_user + admin list to templates."""
    return {
        "current_user": get_current_user(),
        "ADMIN_USER_IDS": ADMIN_USER_IDS,
    }


# ------------------------------
# Authentication Pages
# ------------------------------
@ui_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        username = (request.form.get("username") or "").strip()
        country = (request.form.get("country") or "").strip()
        dob_str = (request.form.get("date_of_birth") or "").strip()

        if not validate_email(email):
            flash("Invalid email format.", "danger")
            return render_template("register.html")

        if not validate_password(password):
            flash("Password must be at least 6 characters.", "danger")
            return render_template("register.html")

        if not validate_username(username):
            flash("Username must be 3–32 chars, letters/numbers/_/-.", "danger")
            return render_template("register.html")

        dob = parse_date_yyyy_mm_dd(dob_str)
        if not dob:
            flash("Date of Birth must be YYYY-MM-DD.", "danger")
            return render_template("register.html")

        existing = query_one("SELECT id FROM users WHERE email = %s", (email,))
        if existing:
            flash("Email already registered.", "danger")
            return render_template("register.html")

        existing_un = query_one(
            "SELECT user_id FROM user_profile WHERE username = %s",
            (username,),
        )
        if existing_un:
            flash("Username already taken.", "danger")
            return render_template("register.html")

        pwd_hash = generate_password_hash(password)

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

        session["user_id"] = user_id
        flash("Registration successful!", "success")
        return redirect(url_for("ui.index"))

    return render_template("register.html")


@ui_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""

        if not email or not password:
            flash("Email and password required.", "danger")
            return render_template("login.html")

        user = query_one("SELECT * FROM users WHERE email = %s", (email,))
        if not user or not check_password_hash(user["password_hash"], password):
            flash("Invalid credentials.", "danger")
            return render_template("login.html")

        session["user_id"] = user["id"]
        flash("Logged in successfully!", "success")
        return redirect(url_for("ui.index"))

    return render_template("login.html")


@ui_bp.route("/logout")
def logout():
    session.clear()
    flash("Logged out.", "info")
    return redirect(url_for("ui.login"))


# ------------------------------
# Home Page
# ------------------------------
@ui_bp.route("/")
def index():
    cursor = books_col.find().sort("views", -1).limit(6)
    popular = []

    for b in cursor:
        popular.append(
            {
                "id": str(b["_id"]),
                "title": b["title"],
                "author": b.get("author"),
                "cover_url": b.get("cover_url"),
                "rating": b.get("rating", {"avg": 0, "count": 0}),
            }
        )

    recs = []

    user = get_current_user()
    if user:
        uid = str(user["id"])

        query = """
    MATCH (u:User {user_id: $uid})-[:READ]->(b:Book)

MATCH (other:User)-[:READ]->(b)
WHERE other.user_id <> $uid

MATCH (other)-[:READ]->(rec:Book)
WHERE rec.book_id <> b.book_id

WITH u, rec, COUNT(*) AS readScore

// LIKE SCORE
OPTIONAL MATCH (other2:User)-[:LIKED]->(b)
WHERE other2.user_id <> $uid
OPTIONAL MATCH (other2)-[:LIKED]->(rec)
WITH u, rec, readScore, COUNT(other2) AS likeScore

// GENRE SCORE
OPTIONAL MATCH (rec)-[:HAS_GENRE]->(g)
OPTIONAL MATCH (b)-[:HAS_GENRE]->(g)
WITH u, rec, readScore, likeScore, COUNT(g) AS genreScore

// TAG SCORE
OPTIONAL MATCH (rec)-[:HAS_TAG]->(t)
OPTIONAL MATCH (b)-[:HAS_TAG]->(t)
WITH u,
     rec,
     readScore,
     likeScore,
     genreScore,
     COUNT(t) AS tagScore

// FINAL SCORING
WITH rec,
     readScore,
     likeScore,
     genreScore,
     tagScore,
     (COALESCE(readScore,0) * 1.0) +
     (COALESCE(likeScore,0) * 2.0) +
     (COALESCE(genreScore,0) * 0.3) +
     (COALESCE(tagScore,0) * 0.6) AS finalScore

RETURN rec.book_id AS id, finalScore
ORDER BY finalScore DESC
LIMIT 8;
        """

        rows = cypher_read(query, {"uid": uid})

        from bson import ObjectId
        for r in rows:
            b = books_col.find_one({"_id": ObjectId(r["id"])})
            if b:
                recs.append({
                    "id": str(b["_id"]),
                    "title": b["title"],
                    "cover_url": b.get("cover_url"),
                    "author": b.get("author"),
                })

    return render_template("index.html", popular_books=popular,  recs=recs)


# ------------------------------
# Book Listing
# ------------------------------
@ui_bp.route("/books")
@login_required
def books():
    user = get_current_user()
    status = user["status"]
    age = _compute_age(user.get("date_of_birth"))

    all_books = []
    cursor = books_col.find()

    for b in cursor:
        # Enforce age restrictions for UI display
        age_rating = int(b.get("age_rating", 0) or 0)
        if age is not None and age < age_rating:
            continue

        all_books.append(
            {
                "id": str(b["_id"]),
                "title": b["title"],
                "author": b.get("author"),
                "cover_url": b.get("cover_url"),
                "premium_only": b.get("premium_only", False),
                "age_rating": age_rating,
                "rating": b.get("rating", {"avg": 0, "count": 0}),
            }
        )

    return render_template("books.html", books=all_books)


# ------------------------------
# Book Detail Page
# ------------------------------
@ui_bp.route("/books/<book_id>")
@login_required
def book_detail(book_id):
    # Convert to ObjectId
    try:
        oid = ObjectId(book_id)
    except Exception:
        flash("Invalid book ID.", "danger")
        return redirect(url_for("ui.books"))

    book = books_col.find_one({"_id": oid})
    if not book:
        flash("Book not found.", "danger")
        return redirect(url_for("ui.books"))

    # Attach string ID for template
    book["mongo_id"] = str(book["_id"])

    user = get_current_user()
    age = _compute_age(user.get("date_of_birth"))
    status = user["status"]

    age_rating = int(book.get("age_rating", 0) or 0)
    locked = book.get("premium_only") and status != "PREMIUM"

    # Age block
    if age is not None and age < age_rating:
        flash("You are too young to view this book.", "danger")

    # Load comments from MySQL
    comments = query_all(
        """
        SELECT c.id,
               c.user_id,
               p.username,
               c.content,
               c.created_at
        FROM comments c
        JOIN user_profile p ON p.user_id = c.user_id
        WHERE c.mongo_book_id = %s
        ORDER BY c.created_at DESC
        """,
        (book_id,),
    )

    return render_template(
        "book_detail.html",
        book=book,
        book_id=str(book["_id"]),
        comments=comments,
        locked=locked,
        age_rating=age_rating,
    )


# ------------------------------
# CART PAGE
# ------------------------------
@ui_bp.route("/cart")
@login_required
def cart():
    user = get_current_user()
    user_id = user["id"]
    key = f"cart:{user_id}"

    raw_cart = redis_client.hgetall(key)  # { book_id: mode }

    items = []
    total = 0.0

    for book_id, mode in raw_cart.items():
        try:
            oid = ObjectId(book_id)
            b = books_col.find_one({"_id": oid})
        except Exception:
            continue

        if not b:
            continue

        base_price = float(b.get("price", 0.0))

        if mode == "RENT":
            price = round(base_price * 0.4, 2)
        elif mode == "HARDCOVER":
            price = round(base_price * 1.5, 2)
        else:  # DIGITAL
            mode = "DIGITAL"
            price = round(base_price, 2)

        total += price

        items.append(
            {
                "id": book_id,
                "title": b["title"],
                "author": b.get("author"),
                "cover_url": b.get("cover_url"),
                "mode": mode,
                "base_price": base_price,
                "price": price,
            }
        )

    return render_template("cart.html", items=items, total=total)

@ui_bp.post("/cart/add/<book_id>")
@login_required
def cart_add(book_id):
    user = get_current_user()
    user_id = user["id"]

    mode = (request.form.get("mode") or "DIGITAL").upper()
    if mode not in ("RENT", "DIGITAL", "HARDCOVER"):
        mode = "DIGITAL"

    # Validate book exists
    try:
        oid = ObjectId(book_id)
        book = books_col.find_one({"_id": oid})
    except Exception:
        book = None

    if not book:
        flash("Book not found.", "danger")
        return redirect(url_for("ui.books"))

    key = f"cart:{user_id}"
    # B: one entry per book; overwrite mode if re-added
    redis_client.hset(key, book_id, mode)

    flash(f"Added '{book['title']}' to cart as {mode.title()}.", "success")
    return redirect(url_for("ui.cart"))


@ui_bp.post("/cart/remove/<book_id>")
@login_required
def cart_remove(book_id):
    user = get_current_user()
    key = f"cart:{user['id']}"

    redis_client.hdel(key, book_id)
    flash("Item removed from cart.", "info")
    return redirect(url_for("ui.cart"))


@ui_bp.post("/cart/checkout")
@login_required
def cart_checkout():
    user = get_current_user()
    user_id = user["id"]
    key = f"cart:{user_id}"

    raw_cart = redis_client.hgetall(key)
    if not raw_cart:
        flash("Your cart is empty.", "warning")
        return redirect(url_for("ui.cart"))

    total_added = 0.0

    for book_id, mode in raw_cart.items():
        try:
            oid = ObjectId(book_id)
            b = books_col.find_one({"_id": oid})
        except Exception:
            continue

        if not b:
            continue

        base_price = float(b.get("price", 0.0))

        if mode == "RENT":
            amount = round(base_price * 0.4, 2)
            purchase_type = "RENT"
            neo_action = "RENT"
        elif mode == "HARDCOVER":
            amount = round(base_price * 1.5, 2)
            purchase_type = "BUY"
            neo_action = "BUY"
        else:
            mode = "DIGITAL"
            amount = round(base_price, 2)
            purchase_type = "BUY"
            neo_action = "BUY"

        # Insert purchase
        execute(
            """
            INSERT INTO purchases (user_id, mongo_book_id, purchase_type, amount)
            VALUES (%s, %s, %s, %s)
            """,
            (user_id, book_id, purchase_type, amount),
        )

        # Neo4j interaction
        track_book_interaction(user_id, book_id, neo_action)

        total_added += amount

    if total_added > 0:
        execute(
            """
            UPDATE users
            SET total_spent = total_spent + %s
            WHERE id = %s
            """,
            (total_added, user_id),
        )

    redis_client.delete(key)

    flash(f"Checkout complete! You spent ${total_added:.2f}.", "success")
    return redirect(url_for("ui.books"))




# ------------------------------
# PROFILE PAGE
# ------------------------------
@ui_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    user = get_current_user()

    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        country = (request.form.get("country") or "").strip()
        dob_str = (request.form.get("date_of_birth") or "").strip()

        updates = []
        params = []

        if username:
            if not validate_username(username):
                flash("Username format invalid.", "danger")
                return render_template("profile.html", user=user)

            # Unique check
            existing_un = query_one(
                """
                SELECT user_id FROM user_profile
                WHERE username = %s AND user_id <> %s
                """,
                (username, user["id"]),
            )
            if existing_un:
                flash("Username already taken.", "danger")
                return render_template("profile.html", user=user)

            updates.append("username = %s")
            params.append(username)

        if country:
            updates.append("country = %s")
            params.append(country)

        if dob_str:
            dob = parse_date_yyyy_mm_dd(dob_str)
            if not dob:
                flash("Invalid date format.", "danger")
                return render_template("profile.html", user=user)

            updates.append("date_of_birth = %s")
            params.append(dob)

        if updates:
            sql = "UPDATE user_profile SET " + ", ".join(updates) + " WHERE user_id = %s"
            params.append(user["id"])
            execute(sql, tuple(params))
            flash("Profile updated.", "success")

        return redirect(url_for("ui.profile"))

    return render_template("profile.html", user=user)


# ------------------------------
# PREMIUM UPGRADE
# ------------------------------
@ui_bp.route("/upgrade", methods=["GET", "POST"])
@login_required
def upgrade():
    user = get_current_user()

    if user["status"] == "PREMIUM":
        flash("You are already a premium user.", "info")
        return redirect(url_for("ui.profile"))

    if request.method == "POST":
        upgrade_price = 9.99

        execute(
            """
            UPDATE users
            SET status = 'PREMIUM',
                total_spent = total_spent + %s
            WHERE id = %s
            """,
            (upgrade_price, user["id"]),
        )

        execute(
            """
            INSERT INTO purchases (user_id, mongo_book_id, purchase_type, amount)
            VALUES (%s, %s, 'UPGRADE', %s)
            """,
            (user["id"], "PREMIUM_UPGRADE", upgrade_price),
        )

        flash("You are now a PREMIUM user!", "success")
        return redirect(url_for("ui.profile"))

    return render_template("upgrade.html")


# ------------------------------
# READ BOOK PAGE (Google Drive Viewer)
# ------------------------------
@ui_bp.route("/read/<book_id>")
@login_required
def read(book_id):
    try:
        oid = ObjectId(book_id)
    except Exception:
        flash("Invalid book ID.", "danger")
        return redirect(url_for("ui.books"))

    user = get_current_user()

    # Check if user purchased or rented
    purchase = query_one(
        """
        SELECT purchase_type
        FROM purchases
        WHERE user_id = %s AND mongo_book_id = %s
        LIMIT 1
        """,
        (user["id"], book_id),
    )

    if not purchase:
        flash("You must buy or rent this book first.", "danger")
        return redirect(url_for("ui.book_detail", book_id=book_id))

    book = books_col.find_one({"_id": oid})
    if not book:
        flash("Book not found.", "danger")
        return redirect(url_for("ui.books"))

    # Increment views in Mongo
    books_col.update_one(
        {"_id": oid},
        {"$inc": {"views": 1}}
    )

    # Track READ in Neo4j
    track_book_interaction(user["id"], book_id, "READ")

    file_id = book.get("file_id")
    if not file_id:
        flash("This book has no file attached.", "danger")
        return redirect(url_for("ui.book_detail", book_id=book_id))

    viewer_url = f"https://drive.google.com/file/d/{file_id}/preview"

    return render_template(
        "read.html",
        book=book,
        viewer_url=viewer_url,
        purchase_type=purchase["purchase_type"],
    )



@ui_bp.post("/books/<book_id>/comment")
@login_required
def ui_comment_book(book_id):
    user = get_current_user()
    content = (request.form.get("content") or "").strip()

    if not content:
        flash("Comment cannot be empty.", "danger")
        return redirect(url_for("ui.book_detail", book_id=book_id))

    execute(
        """
        INSERT INTO comments (user_id, mongo_book_id, content)
        VALUES (%s, %s, %s)
        """,
        (user["id"], book_id, content),
    )

    flash("Comment posted!", "success")
    return redirect(url_for("ui.book_detail", book_id=book_id))


@ui_bp.post("/books/<book_id>/rate")
@login_required
def ui_rate_book(book_id):
    user = get_current_user()
    rating_val = request.form.get("rating")

    if not rating_val or rating_val not in ["1", "2", "3", "4", "5"]:
        flash("Invalid rating.", "danger")
        return redirect(url_for("ui.book_detail", book_id=book_id))

    rating = int(rating_val)

    # Check if already rated
    existing = query_one(
        """
        SELECT id FROM ratings
        WHERE user_id = %s AND mongo_book_id = %s
        """,
        (user["id"], book_id),
    )

    if existing:
        flash("You already rated this book.", "warning")
        return redirect(url_for("ui.book_detail", book_id=book_id))

    # Insert rating in MySQL
    execute(
        """
        INSERT INTO ratings (user_id, mongo_book_id, rating)
        VALUES (%s, %s, %s)
        """,
        (user["id"], book_id, rating),
    )

    # Update MongoDB rating summary
    try:
        oid = ObjectId(book_id)
    except Exception:
        flash("Invalid book ID for rating.", "danger")
        return redirect(url_for("ui.books"))

    book = books_col.find_one({"_id": oid})
    if not book:
        flash("Book not found.", "danger")
        return redirect(url_for("ui.books"))

    current = book.get("rating", {"avg": 0.0, "count": 0})
    old_avg = float(current.get("avg", 0.0))
    old_count = int(current.get("count", 0))

    new_count = old_count + 1
    new_avg = ((old_avg * old_count) + rating) / new_count if new_count > 0 else rating

    books_col.update_one(
        {"_id": oid},
        {
            "$set": {
                "rating.avg": round(new_avg, 2),
                "rating.count": new_count,
            }
        },
    )

    # Track LIKE in Neo4j if rating is high
    if rating >= 4:
        track_book_interaction(user["id"], book_id, "LIKE")

    flash("Thanks for rating!", "success")
    return redirect(url_for("ui.book_detail", book_id=book_id))

@ui_bp.route("/recommendations")
@login_required
def ui_recommendations():
    user = get_current_user()
    uid = str(user["id"])

    query = """
    MATCH (u:User {user_id: $uid})-[:READ]->(b:Book)

MATCH (other:User)-[:READ]->(b)
WHERE other.user_id <> $uid

MATCH (other)-[:READ]->(rec:Book)
WHERE rec.book_id <> b.book_id

WITH u, rec, COUNT(*) AS readScore

// LIKE SCORE
OPTIONAL MATCH (other2:User)-[:LIKED]->(b)
WHERE other2.user_id <> $uid
OPTIONAL MATCH (other2)-[:LIKED]->(rec)
WITH u, rec, readScore, COUNT(other2) AS likeScore

// GENRE SCORE
OPTIONAL MATCH (rec)-[:HAS_GENRE]->(g)
OPTIONAL MATCH (b)-[:HAS_GENRE]->(g)
WITH u, rec, readScore, likeScore, COUNT(g) AS genreScore

// TAG SCORE
OPTIONAL MATCH (rec)-[:HAS_TAG]->(t)
OPTIONAL MATCH (b)-[:HAS_TAG]->(t)
WITH u,
     rec,
     readScore,
     likeScore,
     genreScore,
     COUNT(t) AS tagScore

// FINAL SCORING
WITH rec,
     readScore,
     likeScore,
     genreScore,
     tagScore,
     (COALESCE(readScore,0) * 1.0) +
     (COALESCE(likeScore,0) * 2.0) +
     (COALESCE(genreScore,0) * 0.3) +
     (COALESCE(tagScore,0) * 0.6) AS finalScore

RETURN rec.book_id AS id, finalScore
ORDER BY finalScore DESC
LIMIT 12;

    """

    rows = cypher_read(query, {"uid": uid})

    recs = []
    for r in rows:
        book = books_col.find_one({"_id": ObjectId(r["id"])})
        if book:
            recs.append({
                "id": str(book["_id"]),
                "title": book["title"],
                "author": book.get("author"),
                "cover_url": book.get("cover_url"),
                "score": r["finalScore"]
            })

    return render_template("recommendations.html", recommended=recs)


@ui_bp.route("/recommendations/read")
@login_required
def ui_rec_by_read():
    user = get_current_user()
    uid = str(user["id"])

    query = """
    MATCH (u:User {user_id: $uid})-[:READ]->(b:Book)
    MATCH (other:User)-[:READ]->(b)
    WHERE other.user_id <> $uid
    MATCH (other)-[:READ]->(rec:Book)
    WHERE rec.book_id <> b.book_id
    RETURN rec.book_id AS id,
           rec.title AS title,
           COUNT(*) AS score
    ORDER BY score DESC
    LIMIT 12;
    """

    rows = cypher_read(query, {"uid": uid})

    recs = []
    for r in rows:
        book = books_col.find_one({"_id": ObjectId(r["id"])})
        if book:
            recs.append({
                "id": str(book["_id"]),
                "title": book["title"],
                "author": book.get("author"),
                "cover_url": book.get("cover_url"),
                "score": r["score"]
            })

    return render_template("recommendations_read.html", recommended=recs)


@ui_bp.route("/recommendations/liked")
@login_required
def ui_rec_by_likes():
    user = get_current_user()
    uid = str(user["id"])

    query = """
    MATCH (u:User {user_id: $uid})-[:LIKED]->(b:Book)
    MATCH (other:User)-[:LIKED]->(b)
    WHERE other.user_id <> $uid
    MATCH (other)-[:LIKED]->(rec:Book)
    WHERE rec.book_id <> b.book_id
    RETURN rec.book_id AS id,
           rec.title AS title,
           COUNT(*) AS score
    ORDER BY score DESC
    LIMIT 12;
    """

    rows = cypher_read(query, {"uid": uid})

    recs = []
    for r in rows:
        book = books_col.find_one({"_id": ObjectId(r["id"])})
        if book:
            recs.append({
                "id": str(book["_id"]),
                "title": book["title"],
                "author": book.get("author"),
                "cover_url": book.get("cover_url"),
                "score": r["score"]
            })

    return render_template("recommendations_liked.html", recommended=recs)

@ui_bp.route("/recommendations/book/<book_id>")
@login_required
def ui_rec_by_book(book_id):
    user = get_current_user()
    uid = str(user["id"])

    query = """
    MATCH (b:Book {book_id: $bid})

    MATCH (other:User)-[:READ]->(b)
    MATCH (other)-[:READ]->(rec:Book)
    WHERE rec.book_id <> $bid

    RETURN rec.book_id AS id,
           rec.title AS title,
           COUNT(*) AS score
    ORDER BY score DESC
    LIMIT 12;
    """

    rows = cypher_read(query, {"bid": book_id})

    recs = []
    for r in rows:
        book = books_col.find_one({"_id": ObjectId(r["id"])})
        if book:
            recs.append({
                "id": str(book["_id"]),
                "title": book["title"],
                "author": book.get("author"),
                "cover_url": book.get("cover_url"),
                "score": r["score"]
            })

    return render_template("recommendations_book.html",
                            recommended=recs,
                            original_book_id=book_id)


@ui_bp.route("/reading-profile")
@login_required
def reading_profile():
    user = get_current_user()
    uid = str(user["id"])

    # Query 1: Simple totals
    q_totals = """
    MATCH (u:User {user_id: $uid})-[r]->(b:Book)
    RETURN
        COUNT(CASE WHEN type(r) = 'READ' THEN 1 END) AS reads,
        COUNT(CASE WHEN type(r) = 'LIKED' THEN 1 END) AS likes,
        COUNT(CASE WHEN type(r) = 'RENTED' THEN 1 END) AS rents,
        COUNT(CASE WHEN type(r) = 'BOUGHT' THEN 1 END) AS buys
    """

    totals = cypher_read(q_totals, {"uid": uid})[0]

    # Query 2: Top genres
    q_genres = """
    MATCH (u:User {user_id: $uid})-[:READ]->(b:Book)-[:HAS_GENRE]->(g:Genre)
    RETURN g.name AS genre, COUNT(*) AS count
    ORDER BY count DESC LIMIT 5;
    """

    genres = cypher_read(q_genres, {"uid": uid})

    # Query 3: Top tags
    q_tags = """
    MATCH (u:User {user_id: $uid})-[:READ]->(b:Book)-[:HAS_TAG]->(t:Tag)
    RETURN t.name AS tag, COUNT(*) AS count
    ORDER BY count DESC LIMIT 5;
    """

    tags = cypher_read(q_tags, {"uid": uid})

    # Query 4: Reading timeline (READ counts by day)
    q_timeline = """
    MATCH (u:User {user_id: $uid})-[r:READ]->(b:Book)
    RETURN date(r.last_at) AS day, COUNT(*) AS reads
    ORDER BY day;
    """

    timeline = cypher_read(q_timeline, {"uid": uid})

    return render_template("reading_profile.html",
                           totals=totals,
                           genres=genres,
                           tags=tags,
                           timeline=timeline)




# ------------------------------
# ADMIN UI
# ------------------------------
@ui_bp.route("/admin")
@admin_required
def admin_dashboard():
    return render_template("admin_dashboard.html")
