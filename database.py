
"""
database.py - Handles all SQLite database operations for the Knowledge Archiver.
This includes creating tables, inserting pages, and searching content.
"""

import sqlite3
from datetime import datetime

# Name of the database file
DB_FILE = "knowledge.db"


def get_connection():
    """Create and return a connection to the SQLite database."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row  # Allows accessing columns by name
    return conn


def setup_database():
    """
    Create the database tables if they don't already exist.
    - 'pages' stores the scraped webpage data.
    - 'pages_fts' is a virtual FTS5 table for full-text search.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Create the main pages table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pages (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            url         TEXT UNIQUE,
            title       TEXT,
            content     TEXT,
            date_added  TIMESTAMP,
            tags        TEXT
        )
    """)

    # Attempt to add 'tags' column if table already exists from an older version
    try:
        cursor.execute("ALTER TABLE pages ADD COLUMN tags TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists

    # Create the FTS5 virtual table for full-text search
    # It mirrors title and content from the pages table
    cursor.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS pages_fts
        USING fts5(
            title,
            content,
            content='pages',
            content_rowid='id'
        )
    """)

    # Trigger: keep FTS index updated when a new page is inserted
    cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS pages_ai
        AFTER INSERT ON pages
        BEGIN
            INSERT INTO pages_fts(rowid, title, content)
            VALUES (new.id, new.title, new.content);
        END
    """)

    # Trigger: keep FTS index updated when a page is deleted
    cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS pages_ad
        AFTER DELETE ON pages
        BEGIN
            INSERT INTO pages_fts(pages_fts, rowid, title, content)
            VALUES ('delete', old.id, old.title, old.content);
        END
    """)

    conn.commit()
    conn.close()
    print("[DB] Database ready: knowledge.db")


def url_exists(url):
    """
    Check if a URL is already stored in the database.
    Returns True if it exists, False otherwise.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM pages WHERE url = ?", (url,))
    result = cursor.fetchone()
    conn.close()
    return result is not None


def insert_page(url, title, content, tags=""):
    """
    Insert a scraped page into the database.
    Skips the insert if the URL already exists (no duplicates).
    Returns True on success, False if duplicate or error.
    """
    if url_exists(url):
        print(f"  [SKIP] Already saved: {url}")
        return False

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO pages (url, title, content, date_added, tags)
            VALUES (?, ?, ?, ?, ?)
        """, (url, title, content, datetime.now(), tags))
        conn.commit()
        print(f"  [SAVED] {title or url}")
        return True
    except sqlite3.IntegrityError:
        print(f"  [SKIP] Duplicate URL: {url}")
        return False
    finally:
        conn.close()


def search_pages(query):
    """
    Search saved pages using FTS5 full-text search.
    Returns a list of matching rows with id, url, title, and content snippet.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # FTS5 MATCH query - searches across title and content
    cursor.execute("""
        SELECT p.id, p.url, p.title, p.content, p.tags
        FROM pages p
        JOIN pages_fts f ON p.id = f.rowid
        WHERE pages_fts MATCH ?
        ORDER BY rank
    """, (query,))

    results = cursor.fetchall()
    conn.close()
    return results


def get_all_pages():
    """
    Retrieve all saved pages from the database.
    Returns a list of all rows ordered by date added (newest first).
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, url, title, date_added, tags
        FROM pages
        ORDER BY date_added DESC
    """)
    results = cursor.fetchall()
    conn.close()
    return results


def delete_page(page_id):
    """
    Delete a page from the database by its ID.
    The FTS trigger will automatically update the search index.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM pages WHERE id = ?", (page_id,))
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0


def get_dashboard_stats():
    """
    Calculate simple analytics from the saved knowledge base:
    - total_pages
    - most_common_tag
    - latest_page_title
    """
    conn = get_connection()
    cursor = conn.cursor()

    stats = {
        "total": 0,
        "top_tag": "None",
        "latest": "None"
    }

    cursor.execute("SELECT COUNT(*) as count FROM pages")
    stats["total"] = cursor.fetchone()["count"]

    cursor.execute("SELECT title FROM pages ORDER BY date_added DESC LIMIT 1")
    latest = cursor.fetchone()
    if latest:
        stats["latest"] = latest["title"]

    cursor.execute("SELECT tags FROM pages WHERE tags IS NOT NULL AND tags != ''")
    tag_counts = {}
    for row in cursor.fetchall():
        for tag in row["tags"].split(", "):
            if tag:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

    if tag_counts:
        stats["top_tag"] = max(tag_counts, key=tag_counts.get)

    conn.close()
    return stats