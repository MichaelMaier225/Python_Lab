
import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "products.db"


def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    return conn


def initialize(conn):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id TEXT UNIQUE,
            cluster_id TEXT,
            category TEXT DEFAULT '',
            identifiers TEXT DEFAULT '',
            title TEXT NOT NULL,
            brand TEXT DEFAULT '',
            description TEXT DEFAULT '',
            price REAL,
            currency TEXT DEFAULT '',
            seller TEXT DEFAULT '',
            url TEXT DEFAULT ''
        );

        CREATE INDEX IF NOT EXISTS idx_cluster
        ON products(cluster_id);

        CREATE INDEX IF NOT EXISTS idx_category
        ON products(category);

        CREATE VIRTUAL TABLE IF NOT EXISTS product_search
        USING fts5(
            title,
            brand,
            description,
            content='products',
            content_rowid='id'
        );

        CREATE TRIGGER IF NOT EXISTS products_ai
        AFTER INSERT ON products BEGIN
            INSERT INTO product_search(
                rowid, title, brand, description
            )
            VALUES (
                new.id, new.title, new.brand, new.description
            );
        END;
    """)

    conn.commit()


def search_products(query, limit=20):
    words = re.findall(r"\w+", query.lower())[:8]

    if not words:
        return []

    expression = " AND ".join(
        '"' + word + '"*' for word in words
    )

    with connect() as conn:
        initialize(conn)

        rows = conn.execute("""
            SELECT
                p.id,
                p.source_id,
                p.cluster_id,
                p.category,
                p.identifiers,
                p.title,
                p.brand,
                p.description,
                p.price,
                p.currency,
                p.seller,
                p.url
            FROM product_search
            JOIN products p
                ON p.id = product_search.rowid
            WHERE product_search MATCH ?
            ORDER BY bm25(
                product_search,
                5.0,
                3.0,
                0.5
            )
            LIMIT ?
        """, (expression, limit)).fetchall()

        return [dict(row) for row in rows]


def count_products():
    with connect() as conn:
        initialize(conn)

        return conn.execute(
            "SELECT COUNT(*) FROM products"
        ).fetchone()[0]
