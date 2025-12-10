# seeders/seed_neo4j.py
import os
from neo4j import GraphDatabase
from pymongo import MongoClient

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017/")
MONGO_DB = os.getenv("MONGO_DB", "polyglot_books")


def main():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    client = MongoClient(MONGO_URL)
    db = client[MONGO_DB]
    books_col = db["books"]

    with driver.session() as session:
        # Constraints
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (u:User) REQUIRE u.user_id IS UNIQUE")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (b:Book) REQUIRE b.book_id IS UNIQUE")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (g:Genre) REQUIRE g.name IS UNIQUE")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (t:Tag) REQUIRE t.name IS UNIQUE")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (l:Language) REQUIRE l.code IS UNIQUE")

        # Clear existing book graph (optional)
        session.run("MATCH (b:Book) DETACH DELETE b")

        # Import books
        for b in books_col.find():
            book_id = str(b["_id"])
            title = b["title"]
            genres = b.get("genres", [])
            tags = b.get("tags", [])
            languages = b.get("languages", [])

            session.run(
                """
                MERGE (bk:Book {book_id: $book_id})
                SET bk.title = $title
                """,
                {"book_id": book_id, "title": title},
            )

            for g in genres:
                session.run(
                    """
                    MERGE (bg:Genre {name: $name})
                    MERGE (bk:Book {book_id: $book_id})
                    MERGE (bk)-[:HAS_GENRE]->(bg)
                    """,
                    {"name": g, "book_id": book_id},
                )

            for t in tags:
                session.run(
                    """
                    MERGE (tg:Tag {name: $name})
                    MERGE (bk:Book {book_id: $book_id})
                    MERGE (bk)-[:HAS_TAG]->(tg)
                    """,
                    {"name": t, "book_id": book_id},
                )

            for lang in languages:
                session.run(
                    """
                    MERGE (lg:Language {code: $code})
                    MERGE (bk:Book {book_id: $book_id})
                    MERGE (bk)-[:IN_LANGUAGE]->(lg)
                    """,
                    {"code": lang, "book_id": book_id},
                )

        # Sample users and READ relationships for recommendations
        # user_id 1 and 2 are from MySQL seeding
        book_ids = [str(b["_id"]) for b in books_col.find().limit(10)]
        for i, bid in enumerate(book_ids):
            uid = 1 if i % 2 == 0 else 2
            session.run(
                """
                MERGE (u:User {user_id: $uid})
                MERGE (b:Book {book_id: $bid})
                MERGE (u)-[:READ]->(b)
                """,
                {"uid": str(uid), "bid": bid},
            )

    driver.close()
    print("Neo4j: constraints and book graph seeded.")


if __name__ == "__main__":
    main()
