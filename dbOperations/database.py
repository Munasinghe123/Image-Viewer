import sqlite3
from config import DB_PATH
import os


# ---------------- Database Helper ----------------
class ImageDB:
    def __init__(self):
        self.ensure_table()

    def connect(self):
        print("Using DB:", os.path.abspath(DB_PATH))
        return sqlite3.connect(DB_PATH)

    def ensure_table(self):
        conn = self.connect()
        cur = conn.cursor()

        cur.execute("""
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
        );
        """)

        conn.commit()
        conn.close()

    
    def update_notes(self, image_id, notes_text):
        conn = self.connect()
        cur = conn.cursor()

        cur.execute(
            "UPDATE images SET notes = ? WHERE id = ?",
            (notes_text, image_id)
        )

        conn.commit()
        conn.close()

   