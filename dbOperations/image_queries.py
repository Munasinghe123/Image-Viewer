def get_images_between(db, start_pole, end_pole):

    conn = db.connect()
    cur = conn.cursor()
    
    cur.execute("PRAGMA table_info(images)")
    print(cur.fetchall())

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


def get_images_around_pole(db, pole_id):

    conn = db.connect()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, original_filename, published_path,
               start_pole, end_pole, sequence_no, category, notes
        FROM images
        WHERE pole_id = ?
        ORDER BY sequence_no ASC;
    """, (pole_id,))

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