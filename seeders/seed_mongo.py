# seeders/seed_mongo.py
import os
from pymongo import MongoClient

MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017/")
MONGO_DB = os.getenv("MONGO_DB", "polyglot_books")


def main():
    client = MongoClient(MONGO_URL)
    db = client[MONGO_DB]
    books = db["books"]

    books.drop()

    base_titles = [
        "Whispers of the Sea",
        "Shadows of the Forest",
        "Flames of the Mountain",
        "Echoes of the Stars",
        "Chronicles of the Lost City",
        "Code of the Cosmos",
        "Tales of the Ancient Library",
        "Songs of the Wind",
        "Legends of the Deep",
        "Dreams of Tomorrow",
    ]

    authors = [
        "A. Thompson",
        "J. Rivera",
        "M. Chen",
        "L. Dubois",
        "S. Nakamura",
    ]

    genres_list = [
        ["Fantasy"],
        ["Sci-Fi"],
        ["Horror"],
        ["Romance"],
        ["Non-Fiction"],
        ["Mystery"],
        ["Thriller"],
        ["Self-Help"],
    ]

    tags_pool = [
        "magic", "space", "ai", "dystopia", "pirates",
        "history", "psychology", "programming", "mythology", "adventure"
    ]

    languages_sets = [
        ["en"],
        ["en", "es"],
        ["en", "fr"],
        ["en", "de"],
        ["en", "ja"],
    ]

    docs = []
    idx = 0

    for i in range(1, 41):
        title = f"{base_titles[i % len(base_titles)]} #{i}"
        author = authors[i % len(authors)]
        genres = genres_list[i % len(genres_list)]
        languages = languages_sets[i % len(languages_sets)]
        price = round(4.99 + (i % 5) * 2.0, 2)
        premium_only = (i % 4 == 0)
        age_rating = 18 if (i % 7 == 0) else (13 if (i % 3 == 0) else 0)

        tags = [tags_pool[(i + j) % len(tags_pool)] for j in range(3)]

        doc = {
            "title": title,
            "author": author,
            "price": price,
            "genres": genres,
            "tags": tags,
            "languages": languages,
            "premium_only": premium_only,
            "age_rating": age_rating,
            "rating": {"avg": 0.0, "count": 0},
            "views": 0,
            "cover_url": f"https://via.placeholder.com/400x600?text=Book+{i}",
            "file_id": f"drive_file_{i:02d}",
            "mime_type": "application/pdf",
        }
        docs.append(doc)

    if docs:
        books.insert_many(docs)

    print(f"MongoDB: inserted {len(docs)} books into '{MONGO_DB}.books'.")


if __name__ == "__main__":
    main()
