import psycopg2
import sqlite3

def sync_images():

    # PostgreSQL connection
    pg_conn = psycopg2.connect(
        host="localhost",
        database="drone_image_system",
        user="postgres",
        password="admin",
        port=5432
    )

    pg_cur = pg_conn.cursor()

    # SQLite connection
    sqlite_conn = sqlite3.connect("images.db")
    sqlite_cur = sqlite_conn.cursor()

    # Create SQLite table
    sqlite_cur.execute("""
    CREATE TABLE IF NOT EXISTS images (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        original_filename TEXT,
        published_path TEXT,
        start_pole TEXT,
        end_pole TEXT,
        pole_id TEXT,
        sequence_no INTEGER,
        category TEXT,
        notes TEXT
    )
    """)

    # Fetch from PostgreSQL
    pg_cur.execute("""
    SELECT
        original_filename,
        published_path,
        start_pole,
        end_pole,
        pole_id,
        sequence_no,
        category
    FROM images
    """)

    rows = pg_cur.fetchall()

    inserted = 0

    for row in rows:

        filename, url, start, end, pole_id, seq, category = row

        sqlite_cur.execute(
            "SELECT COUNT(1) FROM images WHERE published_path = ?",
            (url,)
        )

        if sqlite_cur.fetchone()[0] == 0:

            sqlite_cur.execute("""
            INSERT INTO images
            (original_filename, published_path, start_pole, end_pole, pole_id, sequence_no, category)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (filename, url, start, end, pole_id, seq, category))

            inserted += 1

    sqlite_conn.commit()

    print(f"Inserted {inserted} records into SQLite")

    pg_conn.close()
    sqlite_conn.close()