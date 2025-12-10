# poly_app/db_mongo.py
from pymongo import MongoClient
import os

MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017/")
MONGO_DB = os.getenv("MONGO_DB", "polyglot_books")

client = MongoClient(MONGO_URL)
db = client[MONGO_DB]


def get_mongo_db():
    return db
