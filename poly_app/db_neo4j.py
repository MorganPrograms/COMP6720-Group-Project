# poly_app/db_neo4j.py

from neo4j import GraphDatabase
import os

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

_driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))


def cypher_read(query, params=None):
    with _driver.session() as session:
        return list(session.run(query, params or {}))


def cypher_write(query, params=None):
    with _driver.session() as session:
        session.run(query, params or {})


def track_book_interaction(user_id: int, book_id: str, action: str):
    """
    Records interactions between a User and Book in Neo4j.

    action in {"READ", "BUY", "RENT", "LIKE"}
    """
    uid = str(user_id)
    bid = str(book_id)

    if action == "READ":
        q = """
        MERGE (u:User {user_id: $uid})
        MERGE (b:Book {book_id: $bid})
        MERGE (u)-[r:READ]->(b)
        ON CREATE SET r.count = 1, r.last_at = datetime()
        ON MATCH SET r.count = coalesce(r.count, 0) + 1,
                      r.last_at = datetime()
        """
        cypher_write(q, {"uid": uid, "bid": bid})

    elif action == "BUY":
        q = """
        MERGE (u:User {user_id: $uid})
        MERGE (b:Book {book_id: $bid})
        MERGE (u)-[p:BOUGHT]->(b)
        ON CREATE SET p.first_at = datetime()
        """
        cypher_write(q, {"uid": uid, "bid": bid})

    elif action == "RENT":
        q = """
        MERGE (u:User {user_id: $uid})
        MERGE (b:Book {book_id: $bid})
        MERGE (u)-[p:RENTED]->(b)
        ON CREATE SET p.first_at = datetime()
        """
        cypher_write(q, {"uid": uid, "bid": bid})

    elif action == "LIKE":
        q = """
        MERGE (u:User {user_id: $uid})
        MERGE (b:Book {book_id: $bid})
        MERGE (u)-[l:LIKED]->(b)
        """
        cypher_write(q, {"uid": uid, "bid": bid})
