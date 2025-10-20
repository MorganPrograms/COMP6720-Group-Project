from pymongo import MongoClient
from datetime import datetime

def seed_mongo():
    client = MongoClient("mongodb://localhost:27017/")
    db = client["ebooks"]

    db.books.delete_many({})  # clear existing data

    books = [
        {
            "_id": "mongo_001",
            "title": "Free Book 1",
            "author": "Jane Doe",
            "genre": "Fiction",
            "description": "An introductory free e-book for new users.",
            "access_tier": "Free",
            "details": {
                "publication_date": datetime(2020, 5, 10),
                "pages": 180,
                "reviews": [
                    {"user": "alice", "rating": 4, "comment": "Great starter book!"}
                ]
            }
        },
        {
            "_id": "mongo_002",
            "title": "Premium Book 1",
            "author": "John Writer",
            "genre": "Science Fiction",
            "description": "Exclusive premium title for subscribers.",
            "access_tier": "Premium",
            "details": {
                "publication_date": datetime(2022, 3, 15),
                "pages": 220,
                "reviews": [
                    {"user": "bob", "rating": 5, "comment": "Amazing story!"}
                ]
            }
        }
    ]

    db.books.insert_many(books)
    print("✅ MongoDB seeded successfully with 2 books.")

if __name__ == "__main__":
    seed_mongo()
