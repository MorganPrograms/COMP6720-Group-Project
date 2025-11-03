from flask import Flask, flash, render_template, request, redirect, jsonify, session, redirect, url_for, session
from flask_session import Session
import redis
from db.mysql_connection import get_mysql_connection
from db.mongo_connection import get_mongo_connection
from db.neo4j_connection import get_neo4j_driver, create_user_and_book_nodes, create_relationship, get_recommendations
from db.redis_connection import get_redis_client
from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId
from bson.errors import InvalidId
import pymysql
from datetime import datetime

app = Flask(__name__)
app.secret_key = "supersecretkey"
app.config["SESSION_TYPE"] = "redis"
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_USE_SIGNER"] = True
app.config["SESSION_KEY_PREFIX"] = "session:"
app.config["SESSION_REDIS"] = redis.StrictRedis(host="localhost", port=6379, db=0)

# Initialize session
Session(app)

# ---------- ROUTES ----------

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.form
        conn = get_mysql_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO users (username, email, password_hash, subscription_tier)
            VALUES (%s, %s, %s, %s)
        """, (data['username'], data['email'], generate_password_hash(data['password']), data['tier']))
        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for('index'))
    return render_template('register.html')

@app.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    password = request.form['password']
    conn = get_mysql_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM users WHERE email = %s", (email,))
    user = cur.fetchone()
    cur.close()
    conn.close()

    if user and check_password_hash(user['password_hash'], password):
        session['user_id'] = user['id']
        session["email"] = user["email"]
        session['tier'] = user['subscription_tier']
        #redis_client = get_redis_client()
        #redis_client.set(f"user:{user['id']}:tier", user['subscription_tier'])
        return redirect(url_for('dashboard'))
    return "Invalid credentials", 401

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for('index'))


@app.route("/dashboard")
def dashboard():
    """Display all books with access-tier filtering."""
    user_id = session.get("user_id")
    if not user_id:
        flash("Please log in to view your dashboard.", "warning")
        return redirect(url_for("login"))

    # Fetch user tier from MySQL
    conn = get_mysql_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT subscription_tier FROM users WHERE id = %s", (user_id,))
    result = cur.fetchone()
    user_tier = result["subscription_tier"] if result else "Free"
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT b.id AS book_id, AVG(r.rating) AS average_rating, COUNT(r.user_id) AS total_ratings FROM ratings r JOIN books b ON r.book_id = b.mongo_id GROUP BY b.id, b.title ORDER BY average_rating DESC; ")
    ratings = cur.fetchall()
    # Get all books from MongoDB
    mongo_db = get_mongo_connection()
    books = list(mongo_db.books.find())
    combined = zip(books,ratings)

    return render_template("dashboard.html", user_tier=user_tier, combined = combined)



@app.route('/books')
def books():
    mongo_db = get_mongo_connection()
    user_tier = session.get('tier', 'Free')
    query = {} if user_tier == 'Premium' else {"access_tier": "Free"}
    books = list(mongo_db.books.find(query, {"_id": 0}))
    return jsonify(books)


@app.route('/cache')
def cache():
    redis_client = get_redis_client()
    keys = redis_client.keys("user:*")
    data = {key.decode(): redis_client.get(key).decode() for key in keys}
    return jsonify(data)

@app.route('/health')
def health():
    return jsonify({
        "mysql": True,
        "mongo": True,
        "neo4j": True,
        "redis": True
    })


@app.route("/book/<book_id>")
def book_details(book_id):
    """Displays a book's details (from MongoDB) and allows user to rate or subscribe."""
    db = get_mongo_connection()
    book = None

    # Retrieve book info from MongoDB

    book = db.books.find_one({"_id": book_id})
    if not book:
        return "Book not found", 404

    user_id = session.get("user_id")
    user_rating = None

    # Get user's existing rating if available
    conn = get_mysql_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT rating FROM ratings WHERE user_id=%s AND book_id=%s", (user_id, book_id))
    result = cursor.fetchone()
    if result:
        user_rating = result["rating"]
    cursor.close()
    conn.close()

    return render_template("book_details.html", book=book, user_rating=user_rating)


@app.route("/book/<book_id>/rate", methods=["POST"])
def rate_book(book_id):
    """Handles rating submission and updates Neo4j preferences."""
    user_id = session.get("user_id")
    rating = request.form.get("rating")

    if not user_id:
        return redirect(url_for("login"))

    conn = get_mysql_connection()
    cursor = conn.cursor()

    # Insert or update rating
    cursor.execute("""
        INSERT INTO ratings (user_id, book_id, rating, date)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE rating=%s, date=%s
    """, (user_id, book_id, rating, datetime.now(), rating, datetime.now()))
    conn.commit()
    cursor.close()
    conn.close()
    flash('Book rated successfully!', 'success')
    neo4j_driver = get_neo4j_driver()

    # Update Neo4j recommendation relationships
    with neo4j_driver.session() as session_neo:
        session_neo.run("""
            MERGE (u:User {id: $user_id})
            MERGE (b:Book {id: $book_id})
            MERGE (u)-[r:RATED]->(b)
            SET r.value = $rating
        """, user_id=str(user_id), book_id=str(book_id), rating=float(rating))

    return redirect(url_for("book_details", book_id=book_id))


@app.route("/book/<book_id>/subscribe", methods=["POST"])
def subscribe_book(book_id):
    """Handles subscribing a user to a book."""
    user_id = session.get("user_id")

    if not user_id:
        return redirect(url_for("login"))

    conn = get_mysql_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT IGNORE INTO user_books (user_id, book_id, date_subscribed)
        VALUES (%s, %s, %s)
    """, (user_id, book_id, datetime.now()))
    conn.commit()
    cursor.close()
    conn.close()
    flash('Book subscribed successfully!', 'success')
    neo4j_driver = get_neo4j_driver()
    # Update Neo4j relationship
    with neo4j_driver.session() as session_neo:
        session_neo.run("""
            MERGE (u:User {id: $user_id})
            MERGE (b:Book {id: $book_id})
            MERGE (u)-[:SUBSCRIBED_TO]->(b)
        """, user_id=str(user_id), book_id=str(book_id))


    return redirect(url_for("read_book", book_id=book_id))


@app.route("/book/<book_id>/read")
def read_book(book_id):
    """Displays the reading page (linked to dummy PDF) and tracks last read page."""
    user_id = session.get("user_id")
    conn = get_mysql_connection()
    cursor = conn.cursor(dictionary=True)

    # Retrieve last read page
    cursor.execute("SELECT last_page FROM reading_progress WHERE user_id=%s AND book_id=%s", (user_id, book_id))
    result = cursor.fetchone()
    last_page = result["last_page"] if result else 1

    cursor.close()
    conn.close()

    return render_template("read_book.html", book_id=book_id, last_page=last_page)


@app.route("/book/<book_id>/save_progress", methods=["POST"])
def save_progress(book_id):
    """Saves the user's current reading page."""
    user_id = session.get("user_id")
    page = request.form.get("page")

    conn = get_mysql_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO reading_progress (user_id, book_id, last_page, updated_at)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE last_page=%s, updated_at=%s
    """, (user_id, book_id, page, datetime.now(), page, datetime.now()))
    conn.commit()
    cursor.close()
    conn.close()
    flash('Progress saved successfully!', 'success')

    return jsonify({"status": "success"})

@app.route("/recommendations")
def recommendations():
    email = session.get("email", "guest@example.com")
    driver = get_neo4j_driver()
    recs = get_recommendations(driver, email)
    driver.close()
    return render_template("recommendations.html", recs=recs)

@app.route("/recommendations/genre")
def genre_recommendations():
    email = session.get("email", "guest@example.com")

    # Get user's favorite genres based on past reads
    conn = get_mysql_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT genre, COUNT(*) FROM books GROUP BY genre")

    genres = [row[0] for row in cursor.fetchall()]
    cursor.close()

    # Use MongoDB to suggest more books in those genres
    mongo_db = get_mongo_connection()
    genre_books = list(mongo_db.books.find({"genre": {"$in": genres}}, {"_id": 1, "title": 1, "genre": 1, "author": 1}).limit(10))

    return render_template("recommendations_genre.html", genres=genres, books=genre_books)

if __name__ == '__main__':
    app.run(debug=True)
