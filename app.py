from flask import Flask, jsonify, request
from flask_cors import CORS
import mysql.connector
from pymongo import MongoClient
from neo4j import GraphDatabase
import redis

app = Flask(__name__)
CORS(app)

# ------------------------------
# Database Connections
# ------------------------------

# MySQL (ACID demo)
mysql_conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="ebook_service"
)
mysql_cursor = mysql_conn.cursor(dictionary=True)

# MongoDB
mongo_client = MongoClient("mongodb://localhost:27017/")
mongo_db = mongo_client["ebooks"]
mongo_collection = mongo_db["books"]

# Neo4j
neo4j_driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "test1234"))

# Redis
redis_client = redis.StrictRedis(host="localhost", port=6379, db=0, decode_responses=True)


# ------------------------------
# Health Route
# ------------------------------
@app.route("/health")
def health():
    try:
        mysql_cursor.execute("SELECT 1")
        mongo_client.admin.command("ping")
        with neo4j_driver.session() as session:
            session.run("RETURN 1")
        redis_client.ping()
        return jsonify({"status": "All databases are alive ✅"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ------------------------------
# MySQL Routes (CRUD + ACID)
# ------------------------------

@app.route("/mysql/create", methods=["POST"])
def create_mysql():
    data = request.get_json()
    try:
        mysql_cursor.execute(
            "INSERT INTO users (name, email) VALUES (%s, %s)",
            (data["name"], data["email"])
        )
        mysql_conn.commit()
        return jsonify({"message": "User created successfully"}), 201
    except Exception as e:
        mysql_conn.rollback()
        return jsonify({"error": str(e)}), 500


@app.route("/mysql/read", methods=["GET"])
def read_mysql():
    try:
        mysql_cursor.execute("SELECT * FROM users")
        results = mysql_cursor.fetchall()
        print("MySQL Results:", results)  # <— add this
        return jsonify(results), 200
    except Exception as e:
        print("MySQL Error:", e)
        return jsonify({"error": str(e)}), 500


@app.route("/mysql/update/<int:user_id>", methods=["PUT"])
def update_mysql(user_id):
    data = request.get_json()
    try:
        mysql_cursor.execute(
            "UPDATE users SET name=%s, email=%s WHERE id=%s",
            (data["name"], data["email"], user_id)
        )
        mysql_conn.commit()
        return jsonify({"message": "User updated successfully"}), 200
    except Exception as e:
        mysql_conn.rollback()
        return jsonify({"error": str(e)}), 500


@app.route("/mysql/delete/<int:user_id>", methods=["DELETE"])
def delete_mysql(user_id):
    try:
        mysql_cursor.execute("DELETE FROM users WHERE id=%s", (user_id,))
        mysql_conn.commit()
        return jsonify({"message": "User deleted successfully"}), 200
    except Exception as e:
        mysql_conn.rollback()
        return jsonify({"error": str(e)}), 500


# ------------------------------
# MongoDB Route
# ------------------------------

@app.route("/mongo", methods=["GET"])
def read_mongo():
    try:
        data = list(mongo_collection.find({}, {"_id": 0}))
        return jsonify(data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ------------------------------
# Neo4j Route
# ------------------------------

@app.route("/neo4j", methods=["GET"])
def read_neo4j():
    try:
        with neo4j_driver.session() as session:
            query = "MATCH (n) RETURN n LIMIT 25"
            results = session.run(query)
            nodes = [record["n"]._properties for record in results]
        return jsonify(nodes), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ------------------------------
# Redis Route
# ------------------------------

@app.route("/redis", methods=["GET"])
def read_redis():
    try:
        keys = redis_client.keys("*")
        data = {key: redis_client.get(key) for key in keys}
        return jsonify(data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ------------------------------
# Entry Point
# ------------------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
