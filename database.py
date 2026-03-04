import psycopg2
from config import DB_CONFIG


# ---------------- Database Helper ----------------
class ImageDB:
    def __init__(self):
        self.ensure_table()

    def connect(self):
        return psycopg2.connect(**DB_CONFIG)

    def ensure_table(self):
        try:
            conn = self.connect()
            cur = conn.cursor()

            cur.execute("""
            CREATE TABLE IF NOT EXISTS images (
                id SERIAL PRIMARY KEY,
                filename TEXT NOT NULL,
                filepath TEXT NOT NULL UNIQUE,
                start_pole TEXT,
                end_pole TEXT,
                seq_num INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                gps_lat DOUBLE PRECISION,
                gps_lon DOUBLE PRECISION,
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
            SELECT id, filename, filepath, start_pole, end_pole,
                   seq_num, timestamp, gps_lat, gps_lon, notes
            FROM images
            WHERE start_pole = %s AND end_pole = %s
            ORDER BY seq_num ASC;
        """, (start_pole, end_pole))

        rows = cur.fetchall()
        conn.close()

        keys = [
            "id","filename","filepath",
            "start_pole","end_pole",
            "seq_num","timestamp",
            "gps_lat","gps_lon","notes"
        ]

        return [dict(zip(keys, r)) for r in rows]

    def get_images_around_pole(self, pole_id):
        conn = self.connect()
        cur = conn.cursor()

        cur.execute("""
            SELECT id, filename, filepath, start_pole, end_pole,
                   seq_num, timestamp, gps_lat, gps_lon, notes
            FROM images
            WHERE start_pole = %s
              AND (end_pole IS NULL OR end_pole = '')
            ORDER BY seq_num ASC;
        """, (pole_id,))

        rows = cur.fetchall()

        if not rows:
            like = f"%{pole_id}%"
            cur.execute("""
                SELECT id, filename, filepath, start_pole, end_pole,
                       seq_num, timestamp, gps_lat, gps_lon, notes
                FROM images
                WHERE filename ILIKE %s
                ORDER BY seq_num ASC;
            """, (like,))
            rows = cur.fetchall()

        conn.close()

        keys = [
            "id","filename","filepath",
            "start_pole","end_pole",
            "seq_num","timestamp",
            "gps_lat","gps_lon","notes"
        ]

        return [dict(zip(keys, r)) for r in rows]

    def update_notes(self, image_id, notes_text):
        conn = self.connect()
        cur = conn.cursor()

        cur.execute(
            "UPDATE images SET notes = %s WHERE id = %s",
            (notes_text, image_id)
        )

        conn.commit()
        conn.close()

    def filepath_exists(self, filepath):
        conn = self.connect()
        cur = conn.cursor()

        cur.execute(
            "SELECT COUNT(1) FROM images WHERE filepath = %s",
            (filepath,)
        )

        count = cur.fetchone()[0]
        conn.close()

        return count > 0

    def clean_duplicate_filepaths(self):
        conn = self.connect()
        cur = conn.cursor()

        cur.execute("""
            SELECT filepath
            FROM images
            GROUP BY filepath
            HAVING COUNT(*) > 1
        """)

        dupes = [r[0] for r in cur.fetchall()]
        removed = 0

        for fp in dupes:
            cur.execute(
                "SELECT id FROM images WHERE filepath = %s ORDER BY id ASC",
                (fp,)
            )

            ids = [r[0] for r in cur.fetchall()]
            to_delete = ids[1:]

            if to_delete:
                cur.executemany(
                    "DELETE FROM images WHERE id = %s",
                    [(i,) for i in to_delete]
                )
                removed += len(to_delete)

        conn.commit()
        conn.close()

        return removed