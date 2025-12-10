# seeders/seed_mysql.py
import os
import mysql.connector

MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DB = os.getenv("MYSQL_DB", "polyglot_ebooks")


def get_raw_conn(db: str | None = None):
    cfg = {
        "host": MYSQL_HOST,
        "user": MYSQL_USER,
        "password": MYSQL_PASSWORD,
    }
    if db:
        cfg["database"] = db
    return mysql.connector.connect(**cfg)


def create_database():
    conn = get_raw_conn()
    cur = conn.cursor()
    cur.execute(f"CREATE DATABASE IF NOT EXISTS {MYSQL_DB} CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci")
    conn.commit()
    cur.close()
    conn.close()


def create_tables():
    conn = get_raw_conn(MYSQL_DB)
    cur = conn.cursor()

    cur.execute("SET FOREIGN_KEY_CHECKS = 0")

    cur.execute("DROP TABLE IF EXISTS comments")
    cur.execute("DROP TABLE IF EXISTS ratings")
    cur.execute("DROP TABLE IF EXISTS purchases")
    cur.execute("DROP TABLE IF EXISTS user_profile")
    cur.execute("DROP TABLE IF EXISTS users")

    # users
    cur.execute("""
    CREATE TABLE users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        email VARCHAR(255) NOT NULL UNIQUE,
        password_hash VARCHAR(255) NOT NULL,
        status ENUM('FREE','PREMIUM') NOT NULL DEFAULT 'FREE',
        total_spent DECIMAL(10,2) NOT NULL DEFAULT 0.00,
        total_books_read INT NOT NULL DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)

    # user_profile
    cur.execute("""
    CREATE TABLE user_profile (
        user_id INT PRIMARY KEY,
        username VARCHAR(50) NOT NULL UNIQUE,
        country VARCHAR(80),
        date_of_birth DATE,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)

    # purchases
    cur.execute("""
    CREATE TABLE purchases (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        mongo_book_id VARCHAR(64) NOT NULL,
        purchase_type ENUM('BUY','RENT','UPGRADE') NOT NULL,
        amount DECIMAL(10,2) NOT NULL DEFAULT 0.00,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        INDEX idx_purchases_user (user_id),
        INDEX idx_purchases_book (mongo_book_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)

    # ratings
    cur.execute("""
    CREATE TABLE ratings (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        mongo_book_id VARCHAR(64) NOT NULL,
        rating TINYINT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        INDEX idx_ratings_user (user_id),
        INDEX idx_ratings_book (mongo_book_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)

    # comments
    cur.execute("""
    CREATE TABLE comments (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        mongo_book_id VARCHAR(64) NOT NULL,
        content TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        INDEX idx_comments_user (user_id),
        INDEX idx_comments_book (mongo_book_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)

    cur.execute("SET FOREIGN_KEY_CHECKS = 1")
    conn.commit()
    cur.close()
    conn.close()


def seed_users():
    from werkzeug.security import generate_password_hash

    conn = get_raw_conn(MYSQL_DB)
    cur = conn.cursor()

    users = [
        ("user1@example.com", "user1", "FREE", "UserOne", "USA", "1990-01-01"),
        ("admin@example.com", "admin", "PREMIUM", "AdminUser", "UK", "1985-05-10"),
    ]

    for email, pwd, status, username, country, dob in users:
        pwd_hash = generate_password_hash(pwd)
        cur.execute(
            """
            INSERT INTO users (email, password_hash, status, total_spent, total_books_read)
            VALUES (%s, %s, %s, 0.00, 0)
            """,
            (email, pwd_hash, status),
        )
        user_id = cur.lastrowid
        cur.execute(
            """
            INSERT INTO user_profile (user_id, username, country, date_of_birth)
            VALUES (%s, %s, %s, %s)
            """,
            (user_id, username, country, dob),
        )

    conn.commit()
    cur.close()
    conn.close()


def main():
    create_database()
    create_tables()
    seed_users()
    print("MySQL schema and seed data created.")


if __name__ == "__main__":
    main()
