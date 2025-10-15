import os
import sqlite3
from flask import Flask, request, jsonify, render_template

# === Config ===
# Local: use ./db/PitTagRecord.db
# Render (with Disk): set env DB_PATH (e.g., /var/data/PitTagRecord.db)
DB_PATH = os.getenv("DB_PATH", os.path.join("db", "PitTagRecord.db"))

app = Flask(__name__)

# === DB Helpers ===
def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                gate TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                fishid TEXT NOT NULL,
                logfile TEXT NOT NULL
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS imports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL UNIQUE,
                imported_on TEXT NOT NULL
            )
        """)
        conn.commit()

# === Routes ===
@app.route("/")
def index():
    return render_template("index.html")

@app.post("/api/upload")
def api_upload():
    """
    Accepts one or more .log files (multipart/form-data, field name 'files').
    Parses lines starting with TAG, drops dummy tags D01–D07,
    and inserts rows into 'records'. Also records imports.
    """
    if 'files' not in request.files:
        return jsonify({"error": "No files part"}), 400

    files = request.files.getlist('files')
    total_added = 0
    total_dummy = 0
    imported = []

    with get_conn() as conn:
        c = conn.cursor()
        for f in files:
            fname = f.filename or "unknown.log"
            text = f.read().decode("utf-8", errors="ignore")
            lines = text.splitlines()

            # Skip if already imported (same filename)
            try:
                c.execute("INSERT INTO imports (filename, imported_on) VALUES (?, date('now'))", (fname,))
            except sqlite3.IntegrityError:
                # already imported; keep going only if you want to allow duplicates per file
                pass

            batch = []
            dummy = 0
            added = 0

            for line in lines:
                if not line.startswith("TAG"):
                    continue
                parts = line.split()
                if len(parts) < 6:
                    continue
                gate = parts[2]
                ts = parts[3] + " " + parts[4]
                fish = parts[5]
                tag_end = fish[-3:]
                if "D01" <= tag_end <= "D07":
                    dummy += 1
                    continue
                batch.append((gate, ts, fish, fname))

            # Sort by fishid then timestamp (string compare to match Excel text behavior)
            batch.sort(key=lambda r: (r[2], r[1]))

            # Remove "in-between" duplicates for runs with same (fishid, gate)
            cleaned = []
            i = 0
            while i < len(batch):
                start = i
                fid = batch[i][2]
                g = batch[i][0]
                i += 1
                while i < len(batch) and batch[i][2] == fid and batch[i][0] == g:
                    i += 1
                run = batch[start:i]
                if len(run) >= 3:
                    cleaned.append(run[0])      # keep first
                    cleaned.append(run[-1])     # keep last
                else:
                    cleaned.extend(run)

            if cleaned:
                c.executemany("INSERT INTO records (gate, timestamp, fishid, logfile) VALUES (?,?,?,?)", cleaned)
                added = len(cleaned)

            total_dummy += dummy
            total_added += added
            imported.append({"file": fname, "added": added, "dummy_removed": dummy})

        conn.commit()

    return jsonify({
        "summary": {"total_added": total_added, "total_dummy_removed": total_dummy},
        "details": imported
    })

@app.get("/api/records")
def api_records():
    """
    Returns records (optional simple pagination).
    Query params: offset, limit
    """
    offset = int(request.args.get("offset", 0))
    limit = int(request.args.get("limit", 1000))
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT gate, timestamp, fishid, logfile FROM records ORDER BY fishid, timestamp LIMIT ? OFFSET ?", (limit, offset))
        rows = [dict(r) for r in c.fetchall()]
        return jsonify(rows)

@app.get("/api/counts")
def api_counts():
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM records")
        total = c.fetchone()[0]
        c.execute("SELECT COUNT(DISTINCT fishid) FROM records")
        unique_fish = c.fetchone()[0]
        return jsonify({"antenna_hits": total, "unique_fish": unique_fish})

@app.get("/api/imports")
def api_imports():
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT filename, imported_on FROM imports ORDER BY imported_on DESC")
        rows = [dict(r) for r in c.fetchall()]
        return jsonify(rows)

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
