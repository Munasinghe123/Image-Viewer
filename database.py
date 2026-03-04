import sqlite3
from config import DB_PATH


# ---------------- Database Helper ----------------
class ImageDB:
    def __init__(self):
        self.ensure_table()

    def connect(self):
        return sqlite3.connect(DB_PATH)

    def ensure_table(self):
        try:
            conn = self.connect()
            cur = conn.cursor()

            cur.execute("""
            CREATE TABLE IF NOT EXISTS images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_filename TEXT,
                published_path TEXT,
                start_pole TEXT,
                end_pole TEXT,
                sequence_no INTEGER,
                category TEXT,
                notes TEXT
            );
            """)

            conn.commit()
            conn.close()

        except Exception as e:
            print("Error ensuring table:", e)

    def get_images_between(self, start_pole, end_pole):
        conn = self.connect()
        cur = conn.cursor()

        cur.execute("""
            SELECT id, original_filename, published_path,
                start_pole, end_pole, sequence_no, category, notes
            FROM images
            WHERE start_pole = ? AND end_pole = ?
            ORDER BY sequence_no ASC;
        """, (start_pole, end_pole))

        rows = cur.fetchall()
        conn.close()

        keys = [
            "id",
            "filename",
            "published_path",
            "start_pole",
            "end_pole",
            "seq_num",
            "category",
            "notes"
        ]

        return [dict(zip(keys, r)) for r in rows]

    def get_images_around_pole(self, pole_id):
            conn = self.connect()
            cur = conn.cursor()

            cur.execute("""
                SELECT id, original_filename, published_path,
                    start_pole, end_pole, sequence_no, category, notes
                FROM images
                WHERE start_pole = ? OR end_pole = ?
                ORDER BY sequence_no ASC;
            """, (pole_id, pole_id))

            rows = cur.fetchall()
            conn.close()

            keys = [
                "id",
                "filename",
                "published_path",
                "start_pole",
                "end_pole",
                "seq_num",
                "category",
                "notes"
            ]

            return [dict(zip(keys, r)) for r in rows]
    
    def update_notes(self, image_id, notes_text):
        conn = self.connect()
        cur = conn.cursor()

        cur.execute(
            "UPDATE images SET notes = ? WHERE id = ?",
            (notes_text, image_id)
        )

        conn.commit()
        conn.close()

   