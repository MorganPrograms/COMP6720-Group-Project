import os, json, datetime
from flask import Flask, request, jsonify, render_template, redirect
from flask_sqlalchemy import SQLAlchemy
from mongoengine import connect
from neo4j import GraphDatabase
from db.mysql_connection import db
from db.redis_client import get_redis
from mongo.mongo import Ebook
from config import Config
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['SQLALCHEMY_DATABASE_URI'] = Config.MYSQL_URI
db.init_app(app)
with app.app_context():
    db.create_all()

# Mongo
connect(host=Config.MONGO_URI)

# Redis
redis_client = get_redis()

# Neo4j
driver = GraphDatabase.driver(Config.NEO4J_URI, auth=(Config.NEO4J_USER, Config.NEO4J_PASSWORD))

JWT_SECRET = Config.JWT_SECRET

def create_jwt(payload):
    import jwt
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')

def decode_jwt(token):
    import jwt
    return jwt.decode(token, JWT_SECRET, algorithms=['HS256'])

class User(db.Model):
    __tablename__ = 'users'
    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    subscription_tier = db.Column(db.Enum('regular','premium'), default='regular')

class UserBooks(db.Model):
    __tablename__ = 'user_books'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    book_mongo_id = db.Column(db.String(24), nullable=False)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/signup', methods=['GET'])
def signup_page():
    return render_template('signup.html')

@app.route('/login', methods=['GET'])
def login_page():
    return render_template('login.html')

@app.route('/dashboard', methods=['GET'])
def dashboard_page():
    return render_template('dashboard.html')

@app.route('/search_page', methods=['GET'])
def search_page():
    return render_template('search.html')

@app.route('/api/signup', methods=['POST'])
def api_signup():
    data = request.get_json() or request.form
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    tier = data.get('tier','regular')
    if not (username and email and password):
        return jsonify({'error':'missing fields'}), 400
    import bcrypt
    pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    user = User(username=username, email=email, password_hash=pw, subscription_tier=tier)
    db.session.add(user); db.session.commit()
    with driver.session() as s:
        s.run('MERGE (u:User {userId:$id, username:$username})', id=str(user.user_id), username=user.username)
    token = create_jwt({'user_id': user.user_id, 'tier': user.subscription_tier, 'exp': datetime.datetime.utcnow().timestamp()+3600})
    redis_client.setex(f'session:{user.user_id}', 3600, token)
    return jsonify({'token': token})

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json() or request.form
    email = data.get('email'); password = data.get('password')
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'error':'invalid'}), 401
    import bcrypt
    if not bcrypt.checkpw(password.encode(), user.password_hash.encode()):
        return jsonify({'error':'invalid'}), 401
    token = create_jwt({'user_id': user.user_id, 'tier': user.subscription_tier, 'exp': datetime.datetime.utcnow().timestamp()+3600})
    redis_client.setex(f'session:{user.user_id}', 3600, token)
    return jsonify({'token': token})

@app.route('/api/search', methods=['GET'])
def api_search():
    q = request.args.get('q','')
    tier = request.args.get('tier','regular')
    if tier not in ('regular','premium'): tier = 'regular'
    qs = Ebook.objects(__raw__={ "$or":[ {"title":{"$regex":q,"$options":"i"}}, {"author":{"$regex":q,"$options":"i"}}, {"description":{"$regex":q,"$options":"i"}}, {"tags":{"$regex":q,"$options":"i"}} ] })
    results = []
    for b in qs:
        if b.tier == 'premium' and tier!='premium':
            continue
        results.append({'id': str(b.id), 'title': b.title, 'author': b.author, 'tier': b.tier})
    return jsonify(results[:50])

@app.route('/api/choose', methods=['POST'])
def api_choose():
    data = request.get_json() or request.form
    user_id = data.get('user_id'); book_id = data.get('book_id')
    if not (user_id and book_id): return jsonify({'error':'missing'}), 400
    rec = UserBooks(user_id=user_id, book_mongo_id=book_id); db.session.add(rec); db.session.commit()
    Ebook.objects(id=book_id).update_one(inc__popularity=1)
    with driver.session() as s:
        s.run('MERGE (b:Book {mongoId:$mid}) MERGE (u:User {userId:$uid}) MERGE (u)-[:CHOSEN {at: datetime()}]->(b)', mid=book_id, uid=str(user_id))
    return jsonify({'ok':True})

@app.route('/api/recommend', methods=['GET'])
def api_recommend():
    user_id = request.args.get('user_id')
    if not user_id: return jsonify({'error':'missing user_id'}), 400
    with driver.session() as s:
        res = s.run('''
            MATCH (u:User {userId: $uid})-[:CHOSEN]->(b:Book)<-[:CHOSEN]-(other:User)-[:CHOSEN]->(rec:Book)
            WHERE NOT (u)-[:CHOSEN]->(rec)
            RETURN rec.mongoId AS id, COUNT(*) AS score ORDER BY score DESC LIMIT 10
        ''', uid=str(user_id))
        ids = [r['id'] for r in res]
    books = Ebook.objects(id__in=ids)
    return jsonify([{'id':str(b.id),'title':b.title,'author':b.author} for b in books])

@app.route('/api/profile/<int:user_id>', methods=['GET'])
def api_profile(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    return jsonify({
        'user_id': user.user_id'
        'username': user.username,
        'email': user.email,
        'subscription_tier': user.subscription_tier
    })
if __name__ == '__main__':
    app.run(port=Config.PORT, debug=True)
