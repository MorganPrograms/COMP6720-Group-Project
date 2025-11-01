from neo4j import GraphDatabase
from mongo.models import Ebook
from mongoengine import connect
import os
connect(host=os.getenv('MONGO_URI','mongodb://localhost:27017/ebook_catalog'))
driver = GraphDatabase.driver(os.getenv('NEO4J_URI','bolt://localhost:7687'), auth=(os.getenv('NEO4J_USER','neo4j'), os.getenv('NEO4J_PASSWORD','test1234')))
books = list(Ebook.objects())
with driver.session() as s:
    s.run('CREATE CONSTRAINT IF NOT EXISTS FOR (b:Book) REQUIRE b.mongoId IS UNIQUE')
    for b in books:
        s.run('MERGE (b:Book {mongoId:$id, title:$title, author:$author})', id=str(b.id), title=b.title, author=b.author)
print('Neo4j seeded')
