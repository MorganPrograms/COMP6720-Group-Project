import os
from datetime import datetime
import mysql.connector
from mongoengine import connect
from bson import ObjectId
from neo4j import GraphDatabase

# ---------------------------------------------------
# 1. CONNECT TO MONGO
# ---------------------------------------------------
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/ebooks")

connect(host=MONGO_URI)
from mongoengine.connection import get_db
db = get_db()
mongo_books = db["books"]

# ---------------------------------------------------
# 2. CONNECT TO MYSQL
# ---------------------------------------------------
mysql_db = mysql.connector.connect(
    host=os.getenv("MYSQL_HOST", "localhost"),
    user=os.getenv("MYSQL_USER", "root"),
    password=os.getenv("MYSQL_PASS", ""),
    database=os.getenv("MYSQL_DB", "ebook_service")
)
cursor = mysql_db.cursor(dictionary=True)

# ---------------------------------------------------
# 3. CONNECT TO NEO4J
# ---------------------------------------------------
NEO_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO_USER = os.getenv("NEO4J_USER", "neo4j")
NEO_PASS = os.getenv("NEO4J_PASS", "test1234")

driver = GraphDatabase.driver(NEO_URI, auth=(NEO_USER, NEO_PASS))

# ---------------------------------------------------
# UTILITY FUNCTIONS
# ---------------------------------------------------
def execute(tx, query, params=None):
    tx.run(query, params or {})




def build_constraints():
    print("🔧 Creating Neo4j constraints...")
    with driver.session() as session:
        session.run("CREATE CONSTRAINT user_id IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE")
        session.run("CREATE CONSTRAINT book_id IF NOT EXISTS FOR (b:Book) REQUIRE b.id IS UNIQUE")
        session.run("CREATE CONSTRAINT author_name IF NOT EXISTS FOR (a:Author) REQUIRE a.name IS UNIQUE")
        session.run("CREATE CONSTRAINT genre_name IF NOT EXISTS FOR (g:Genre) REQUIRE g.name IS UNIQUE")
        session.run("CREATE CONSTRAINT year_value IF NOT EXISTS FOR (y:Year) REQUIRE y.value IS UNIQUE")
    print("✅ Constraints created.\n")


# ---------------------------------------------------
# IMPORT BOOK METADATA FROM MONGO
# ---------------------------------------------------
book_lookup = {}   # SQL id → Mongo ObjectID string

def import_books():
    print("📚 Importing books from MongoDB...")

    count = 0

    with driver.session() as session:
        for b in mongo_books.find():
            mongo_id = str(b["_id"])

            # you MUST have stored sql_id in Mongo
            if "_id" not in b:
                print(f"[WARN] Book {b.get('title')} missing sql_id → skipping")
                continue

            sql_id = b["_id"]
            book_lookup[sql_id] = mongo_id

            title = b.get("title", "Unknown Title")
            author = b.get("author", "Unknown Author")
            genre = b.get("genre", "Unknown Genre")
            pub_year = b["details"]["publication_date"]

            session.run("""
                MERGE (bk:Book {id: $id})
                    SET bk.title = $title
                MERGE (a:Author {name: $author})
                MERGE (g:Genre {name: $genre})
                MERGE (y:Year {value: $year})

                MERGE (a)-[:WROTE]->(bk)
                MERGE (bk)-[:BELONGS_TO]->(g)
                MERGE (bk)-[:PUBLISHED_IN]->(y)
            """, {
                "id": mongo_id,
                "title": title,
                "author": author,
                "genre": genre,
                "year": pub_year
            })

            count += 1

    print(f"✅ Imported {count} books.\n")


# ---------------------------------------------------
# IMPORT USER ACTIVITY
# ---------------------------------------------------
def import_activity(table, rel_type):
    print(f"🔄 Importing {rel_type} from '{table}'...")

    cursor.execute(f"SELECT user_id, book_id FROM {table}")
    rows = cursor.fetchall()

    imported = 0
    skipped = 0

    with driver.session() as session:
        for row in rows:
            user_id = row["user_id"]
            sql_book = row["book_id"]

            if sql_book not in book_lookup:
                print(f"[WARN] SQL book_id={sql_book} missing in Mongo → skipped")
                skipped += 1
                continue

            bk = book_lookup[sql_book]

            session.run(f"""
                MERGE (u:User {{id: $uid}})
                MERGE (b:Book {{id: $bid}})
                MERGE (u)-[:{rel_type}]->(b)
            """, {"uid": str(user_id), "bid": bk})

            imported += 1

    print(f"  → Imported {imported}, skipped {skipped}\n")


# ---------------------------------------------------
# MASTER IMPORT PROCESS
# ---------------------------------------------------
def run_import():

    build_constraints()
    import_books()
    import_activity("user_books", "SUBSCRIBED_TO")
    import_activity("ratings", "RATED")
    import_activity("reading_progress", "READ")
    print("🎉 IMPORT COMPLETE — Neo4j is fully synced!\n")


# ---------------------------------------------------
# RUN SCRIPT
# ---------------------------------------------------
run_import()

driver.close()
mysql_db.close()
