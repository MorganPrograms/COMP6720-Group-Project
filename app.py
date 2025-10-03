import os
import jwt
import bcrypt
import redis
import datetime
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from mongoengine import connect
from neo4j import GraphDatabase

from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)

# MySQL setup
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("MYSQL_URI")
db = SQLAlchemy(app)

class User(db.Model):
    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    subscription_tier = db.Column(db.Enum('regular', 'premium'), default='regular')

class UserBook(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)
    book_mongo_id = db.Column(db.String(24), nullable=False)

# Mongo setup
from models.mongo import Ebook
connect(host=os.getenv("MONGO_URI"))

# Redis setup
redis_client = redis.from_url(os.getenv("REDIS_URI"))

# Neo4j setup
driver = GraphDatabase.driver(os.getenv("NEO4J_URI"), auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD")))

JWT_SECRET = os.getenv("JWT_SECRET")

def create_jwt(payload):
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

def decode_jwt(token):
    return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])

@app.route("/signup", methods=["POST"])
def signup():
    data = request.json
    hashed = bcrypt.hashpw(data['password'].encode(), bcrypt.gensalt())
    user = User(username=data['username'], email=data['email'], password_hash=hashed)
    db.session.add(user)
    db.session.commit()
    with driver.session() as session:
        session.run("MERGE (u:User {userId: $id, username: $username})", id=user.user_id, username=user.username)
    return jsonify({"message": "User created"})

@app.route("/login", methods=["POST"])
def login():
    data = request.json
    user = User.query.filter_by(email=data['email']).first()
    if not user or not bcrypt.checkpw(data['password'].encode(), user.password_hash.encode()):
        return jsonify({"error": "Invalid credentials"}), 401
    token = create_jwt({"user_id": user.user_id, "tier": user.subscription_tier, "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)})
    redis_client.setex(f"session:{user.user_id}", 3600, token)
    return jsonify({"token": token})

@app.route("/search", methods=["GET"])
def search():
    q = request.args.get("q", "")
    tier = request.args.get("tier", "regular")
    books = Ebook.objects(tier__in=[tier, "regular"], title__icontains=q)
    return jsonify([{ "id": str(b.id), "title": b.title, "author": b.author } for b in books])

@app.route("/choose", methods=["POST"])
def choose():
    data = request.json
    user_id, book_id = data['user_id'], data['book_id']
    entry = UserBook(user_id=user_id, book_mongo_id=book_id)
    db.session.add(entry)
    db.session.commit()
    book = Ebook.objects(id=book_id).first()
    if book:
        book.popularity += 1
        book.save()
    with driver.session() as session:
        session.run("MATCH (u:User {userId: $uid}), (b:Book {mongoId: $bid}) MERGE (u)-[:CHOSEN]->(b)", uid=user_id, bid=book_id)
    return jsonify({"message": "Book chosen"})

@app.route("/recommend", methods=["GET"])
def recommend():
    user_id = request.args.get("user_id")
    with driver.session() as session:
        result = session.run("""
            MATCH (u:User {userId: $uid})-[:CHOSEN]->(b:Book)<-[:CHOSEN]-(o:User)-[:CHOSEN]->(rec:Book)
            WHERE NOT (u)-[:CHOSEN]->(rec)
            RETURN rec.mongoId AS book_id, COUNT(*) AS score
            ORDER BY score DESC LIMIT 5
        """, uid=int(user_id))
        recs = [record["book_id"] for record in result]
    books = Ebook.objects(id__in=recs)
    return jsonify([{ "id": str(b.id), "title": b.title } for b in books])

if __name__ == "__main__":
    db.create_all()
    app.run(debug=True)
