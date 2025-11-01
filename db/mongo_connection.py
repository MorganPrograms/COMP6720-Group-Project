from pymongo import MongoClient

def get_mongo_connection():
    client = MongoClient("mongodb://localhost:27017/")
    db = client["ebooks"]
    return db
