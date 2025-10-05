import os
from dotenv import load_dotenv
from mongo.mongo import Ebook
from mongoengine import connect
from neo4j import GraphDatabase
from datetime import datetime
load_dotenv()

connect(host=os.getenv('MONGO_URI','mongodb://localhost:27017/ebooks'))

driver = GraphDatabase.driver(os.getenv('NEO4J_URI','bolt://localhost:7687'), auth=(os.getenv('NEO4J_USER','neo4j'), os.getenv('NEO4J_PASSWORD','admin')))

sample_books = [
    {"title": "Intro to Databases", "author": "Jane Doe", "description": "Learn DB basics", "tags": ["database","intro"], "published_date": datetime(2023,1,1), "tier":"regular"},
    {"title": "Advanced Graph Theory", "author": "John Smith", "description": "Deep dive into graphs", "tags": ["graph","theory"], "published_date": datetime(2024,5,10), "tier":"premium"},
    {"title": "Cloud Patterns", "author": "Alexa Cloud", "description": "Design patterns for cloud apps", "tags": ["cloud","patterns"], "published_date": datetime(2022,7,7), "tier":"regular"}
]

Ebook.drop_collection()
ids = []
for b in sample_books:
    doc = Ebook(**b).save()
    ids.append(str(doc.id))

with driver.session() as s:
    for i in ids:
        s.run('MERGE (b:Book {mongoId:$id, title:$title})', id=i, title=Ebook.objects(id=i).first().title)

print('Seeded MongoDB and Neo4j with sample books')