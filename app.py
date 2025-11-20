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
def sync_book_to_neo4j(book):
    neo4j_driver = get_neo4j_driver()
    with neo4j_driver.session() as session_neo:
        session_neo.run("""
            MERGE (b:Book {id: $id})
            SET b.title = $title

            MERGE (a:Author {name: $author})
            MERGE (g:Genre {name: $genre})
            MERGE (y:Year {value: $year})

            MERGE (a)-[:WROTE]->(b)
            MERGE (b)-[:BELONGS_TO]->(g)
            MERGE (b)-[:PUBLISHED_IN]->(y)
        """, id=str(book["_id"]), title=book["title"],
           author=book["author"], genre=book["genre"], year=book["year"])

        
def get_recommended_books(user_id):
    neo4j_driver = get_neo4j_driver()
    with neo4j_driver.session() as session_neo:
        result = session_neo.run("""
            MATCH (u:User {id: $user_id})-[:READ|SUBSCRIBED_TO|RATED]->(b1:Book)
            OPTIONAL MATCH (b1)<-[:WROTE]-(a:Author)
            OPTIONAL MATCH (b1)-[:BELONGS_TO]->(g:Genre)
            
            MATCH (b2:Book)
            WHERE NOT (u)-[:READ|SUBSCRIBED_TO|RATED]->(b2)
              AND (
                (EXISTS((b2)<-[:WROTE]-(a))) OR
                (EXISTS((b2)-[:BELONGS_TO]->(g)))
              )
            RETURN DISTINCT b2.id AS book_id
            LIMIT 10
        """, user_id=str(user_id))
        return [record["book_id"] for record in result]

    
def record_user_action(user_id, book_id, action, rating_value=None):
    neo4j_driver = get_neo4j_driver()
    with neo4j_driver.session() as session:
        if action == "subscribe":
            session.run("""
                MERGE (u:User {id: $user_id})
                MERGE (b:Book {id: $book_id})
                MERGE (u)-[:SUBSCRIBED_TO]->(b)
            """, user_id=str(user_id), book_id=str(book_id))

        elif action == "read":
            session.run("""
                MERGE (u:User {id: $user_id})
                MERGE (b:Book {id: $book_id})
                MERGE (u)-[:READ]->(b)
            """, user_id=str(user_id), book_id=str(book_id))

        elif action == "rate" and rating_value:
            session.run("""
                MERGE (u:User {id: $user_id})
                MERGE (b:Book {id: $book_id})
                MERGE (u)-[r:RATED]->(b)
                SET r.value = $rating_value
            """, user_id=str(user_id), book_id=str(book_id), rating_value=rating_value)


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
    user_id = session['user_id']
    search_query = request.args.get('search', '').strip()
    genre_filter = request.args.get('genre', '').strip()

    conn = get_mysql_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT b.* FROM books b
        JOIN user_books ub ON ub.book_id = b.mongo_id
        WHERE ub.user_id = %s
    """, (user_id,))
    subscribed_books = cur.fetchall()
    cur.execute("SELECT subscription_tier FROM users WHERE id = %s", (user_id,))
    result = cur.fetchone()
    user_tier = result["subscription_tier"] if result else "Free"
    cur.execute("SELECT b.id AS book_id, AVG(r.rating) AS average_rating, COUNT(r.user_id) AS total_ratings FROM ratings r JOIN books b ON r.book_id = b.mongo_id GROUP BY b.id, b.title ORDER BY average_rating DESC; ")
    ratings = cur.fetchall()
    # Get all books from MongoDB
    mongo_db = get_mongo_connection()
    books = list(mongo_db.books.find())
    combined = zip(books,ratings)
    recommended_book_ids = get_recommended_books(user_id)
    # Fetch details from MongoDB
    recommended_books = list(mongo_db.books.find({"_id": {"$in": recommended_book_ids}}))

    if search_query or genre_filter:
        query = "SELECT * FROM books WHERE 1=1"
        params = []
        if search_query:
            query += " AND (title LIKE %s OR genre LIKE %s)"
            params.extend([f"%{search_query}%", f"%{search_query}%"])
        if genre_filter:
            query += " AND genre = %s"
            params.append(genre_filter)
        cur.execute(query, tuple(params))
    else:
        cur.execute("SELECT * FROM books ORDER BY title ASC")
    all_books = cur.fetchall()

    cur.close()
    
    return render_template('dashboard.html',
                           subscribed_books=subscribed_books,
                           recommended_books=recommended_books,
                           all_books=all_books,
                           search_query=search_query,
                           genre_filter=genre_filter,
                           subscription_tier=user_tier,books = books, ratings = ratings, combined = combined)







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
    cursor.execute("SELECT * FROM ratings WHERE user_id = %s AND book_id = %s", (user_id, book_id))
    existing_rating = cursor.fetchone()

    if existing_rating:
        flash("You’ve already rated this book. You can’t rate it again.", "warning")
        cursor.close()
        return redirect(url_for('book_details', book_id = book_id))

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


@app.route('/search', methods=['GET'])
def search_books():
    query = request.args.get('query', '').strip()
    filter_by = request.args.get('filter_by', 'title').strip()  # title, author, date, genre

    # No input, show all
    if not query:
        conn = get_mysql_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM books")
        books = cur.fetchall()
        cur.close()

        results = []
        for b in books:
            mongo_db = get_mongo_connection()
            mongo_book = mongo_db.books.find_one({"_id": b['mongo_id']})
            if mongo_book:
                results.append({**b, **mongo_book})
        return render_template('search.html', books=results)

    results = []

    # --- Search by Title or Genre (works on both MySQL + MongoDB) ---
    if filter_by in ['title', 'genre']:
        conn = get_mysql_connection()
        cur = conn.cursor()
        cur.execute(f"SELECT * FROM books WHERE {filter_by} LIKE %s", (f"%{query}%",))
        mysql_results = cur.fetchall()
        cur.close()

        for b in mysql_results:
            mongo_book = mongo_db.books.find_one({"_id": b['mongo_id']})
            if mongo_book:
                results.append({**b, **mongo_book})

    # --- Search by Author (MongoDB only) ---
    elif filter_by == 'author':
        mongo_results = mongo_db.books.find({"author": {"$regex": query, "$options": "i"}})
        for m in mongo_results:
            conn = get_mysql_connection()
            cur = conn.cursor()
            cur.execute("SELECT * FROM books WHERE mongo_id = %s", (m['_id'],))
            mysql_book = cur.fetchone()
            cur.close()
            if mysql_book:
                results.append({**mysql_book, **m})

    # --- Search by Publication Date (MongoDB only) ---
    elif filter_by == 'date':
        try:
            query_date = datetime.strptime(query, "%Y-%m-%d")
            mongo_results = mongo_db.books.find({
                "details.publication_date": {
                    "$gte": query_date,
                    "$lt": query_date.replace(hour=23, minute=59, second=59)
                }
            })
            for m in mongo_results:

                conn = get_mysql_connection()
                cur = conn.cursor()
                
                cur.execute("SELECT * FROM books WHERE mongo_id = %s", (m['_id'],))
                mysql_book = cur.fetchone()
                cur.close()
                if mysql_book:
                    results.append({**mysql_book, **m})
        except ValueError:
            return render_template('search.html', books=[], error="Invalid date format. Use YYYY-MM-DD")

    return render_template('search.html', books=results, query=query, filter_by=filter_by)

@app.route('/upgrade', methods=['GET', 'POST'])
def upgrade_account():
    if 'user_id' not in session:
        flash("You must be logged in to upgrade your account.", "danger")
        return redirect(url_for('login'))

    user_id = session['user_id']

    if request.method == 'POST':
        # Simulate payment success
        conn = get_mysql_connection()
        cur = conn.cursor()
        cur.execute("UPDATE users SET subscription_tier = 'Premium' WHERE id = %s", (user_id,))
        conn.commit()
        cur.close()

        session['subscription_tier'] = 'Premium'
        flash("Your account has been upgraded to Premium! 🎉", "success")

        # Redirect back to last attempted book if stored
        last_book = session.pop('attempted_book', None)
        if last_book:
            return redirect(url_for('view_book', mongo_id=last_book))

        return redirect(url_for('dashboard'))

    return render_template('upgrade.html')

@app.route("/account")
def account():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    conn = get_mysql_connection()
    cur = conn.cursor()
    cur.execute("SELECT username, email, subscription_tier FROM users WHERE id = %s", (user_id,))
    user = cur.fetchone()
    cur.close()
    conn.close()

    return render_template("account.html", user=user)


@app.route("/update_profile", methods=["POST"])
def update_profile():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    username = request.form["username"]
    email = request.form["email"]

    conn = get_mysql_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE users SET username=%s, email=%s WHERE id=%s
    """, (username, email, user_id))
    conn.commit()
    cur.close()
    conn.close()

    flash("Profile updated successfully!")
    return redirect(url_for("account"))


@app.route("/change_password", methods=["POST"])
def change_password():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    current_pw = request.form["current_password"]
    new_pw = request.form["new_password"]

    conn = get_mysql_connection()
    cur = conn.cursor()
    cur.execute("SELECT password_hash FROM users WHERE id = %s", (user_id,))
    user = cur.fetchone()

    if not user or not check_password_hash(user["password_hash"], current_pw):
        flash("Incorrect current password.")
        return redirect(url_for("account"))

    new_hash = generate_password_hash(new_pw)
    cur.execute("UPDATE users SET password_hash = %s WHERE id = %s", (new_hash, user_id))
    conn.commit()
    cur.close()
    conn.close()

    flash("Password updated successfully!")
    return redirect(url_for("account"))


@app.route("/upgrade_to_premium", methods=["POST"])
def upgrade_to_premium():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    # Simulated card info (demo only)
    cc_number = request.form["cc_number"]
    cc_exp = request.form["cc_exp"]
    cc_cvv = request.form["cc_cvv"]

    conn = get_mysql_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET subscription_tier = 'Premium' WHERE id = %s", (user_id,))
    conn.commit()
    cur.close()
    conn.close()

    flash("You have successfully upgraded to Premium! 🎉")
    return redirect(url_for("account"))

if __name__ == '__main__':
    app.run(debug=True)
