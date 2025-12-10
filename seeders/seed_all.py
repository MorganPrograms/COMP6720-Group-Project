# seeders/seed_all.py
from seeders.seed_mysql import main as seed_mysql
from seeders.seed_mongo import main as seed_mongo
from seeders.seed_neo4j import main as seed_neo4j


def main():
    seed_mysql()
    seed_mongo()
    seed_neo4j()
    print("All databases seeded.")


if __name__ == "__main__":
    main()
