# poly_app/db_mysql.py
import mysql.connector
from mysql.connector import pooling, Error
import os

MYSQL_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", ""),
    "database": os.getenv("MYSQL_DB", "polyglot_ebooks"),
}

pool = pooling.MySQLConnectionPool(
    pool_name="mysql_pool",
    pool_size=10,
    **MYSQL_CONFIG
)


def get_conn():
    try:
        return pool.get_connection()
    except Error as e:
        raise RuntimeError(f"MySQL connection failed: {e}")


def query_one(sql, params=()):
    conn = get_conn()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(sql, params)
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row


def query_all(sql, params=()):
    conn = get_conn()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(sql, params)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows


def execute(sql, params=()):
    """
    Execute a single statement and commit.
    Returns cursor.lastrowid (or None if not applicable).
    """
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(sql, params)
    last_id = cursor.lastrowid
    conn.commit()
    cursor.close()
    conn.close()
    return last_id


def execute_transaction(operations):
    """
    Executes a list of SQL operations atomically.
    operations = [(sql, params), ...]
    """
    conn = get_conn()
    cursor = conn.cursor()
    try:
        for sql, params in operations:
            cursor.execute(sql, params)
        conn.commit()
    except Error as e:
        conn.rollback()
        raise RuntimeError(f"Transaction failed: {e}")
    finally:
        cursor.close()
        conn.close()
