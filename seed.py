import os
from dotenv import load_dotenv
from mongoengine import connect
from models.mongo import Ebook
from datetime import datetime
from neo4j import GraphDatabase

load_dotenv()

connect(host=os.getenv("MONGO_URI"))

driver = GraphDatabase.driver(os.getenv("NEO4J_URI"), auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD")))

sample_books = [
    {"title": "Intro to Databases", "author": "Jane Doe", "description": "Learn DB basics", "tags": ["database", "intro"], "published_date": datetime(2023, 1, 1), "tier": "regular"},
    {"title": "Advanced Graph Theory", "author": "John Smith", "description": "Deep dive into graphs", "tags": ["graph", "theory"], "published_date": datetime(2024, 5, 10), "tier": "premium"}
]

for book in sample_books:
    doc = Ebook(**book)
    doc.save()
    with driver.session() as session:
        session.run("MERGE (b:Book {mongoId: $id, title: $title})", id=str(doc.id), title=doc.title)

print("Seeded MongoDB and Neo4j")
