import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "asin_checker")
DB_USER = os.getenv("DB_USER", "juanroussille")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")


def get_connection():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )


def save_result(asin: str, status: str, reason: str | None):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO asin_results (asin, status, reason)
                VALUES (%s, %s, %s)
                ON CONFLICT DO NOTHING
                """,
                (asin, status, reason),
            )
        conn.commit()
    finally:
        conn.close()


def get_cached_result(asin: str) -> dict | None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT asin, status, reason, checked_at
                FROM asin_results
                WHERE asin = %s
                AND checked_at > NOW() - INTERVAL '24 hours'
                ORDER BY checked_at DESC
                LIMIT 1
                """,
                (asin,),
            )
            row = cur.fetchone()
            if row:
                return {
                    "asin": row[0],
                    "status": row[1],
                    "reason": row[2],
                    "cached": True,
                    "checked_at": str(row[3]),
                }
            return None
    finally:
        conn.close()