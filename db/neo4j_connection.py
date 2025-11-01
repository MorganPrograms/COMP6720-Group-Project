# db/neo4j_connection.py
from neo4j import GraphDatabase
from pymongo import MongoClient

def get_mongo_connection():
    client = MongoClient("mongodb://localhost:27017/")
    db = client["ebooks"]
    return db

def get_neo4j_driver():
    uri = "bolt://localhost:7687"
    user = "neo4j"
    password = "test1234"  # update if needed
    driver = GraphDatabase.driver(uri, auth=(user, password))
    return driver

def close_driver(driver):
    driver.close()

def create_user_and_book_nodes(driver, user_email, book_id):
    # Fetch genre from MongoDB
    mongo_db = get_mongo_connection()
    book = mongo_db.books.find_one({"_id": book_id})
    genre = book.get("genre", "Unknown") if book else "Unknown"

    with driver.session() as session:
        session.run("""
            MERGE (u:User {email: $user_email})
            MERGE (b:Book {id: $book_id})
            SET b.genre = $genre
        """, user_email=user_email, book_id=str(book_id), genre=genre)

def create_relationship(driver, user_email, book_id, relation_type, rating=None):
    with driver.session() as session:
        if relation_type == "RATED":
            session.run("""
                MATCH (u:User {email: $user_email}), (b:Book {id: $book_id})
                MERGE (u)-[r:RATED]->(b)
                SET r.value = $rating
            """, user_email=user_email, book_id=str(book_id), rating=rating)
        else:
            session.run(f"""
                MATCH (u:User {{email: $user_email}}), (b:Book {{id: $book_id}})
                MERGE (u)-[:{relation_type}]->(b)
            """, user_email=user_email, book_id=str(book_id))

def get_recommendations(driver, user_email, limit=5):
    with driver.session() as session:
        result = session.run("""
            MATCH (u:User {email: $user_email})-[:RATED|READ|LIKES]->(b1:Book)
            MATCH (b1)<-[:RATED|READ|LIKES]-(other:User)-[:RATED|READ|LIKES]->(b2:Book)
            WHERE NOT (u)-[:RATED|READ|LIKES]->(b2)
            RETURN DISTINCT b2.id AS book_id, b2.genre AS genre
            LIMIT $limit
        """, user_email=user_email, limit=limit)
        return [record.data() for record in result]
