import os
from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from datetime import date

app = Flask(__name__)

# Connect to Postgres using the DATABASE_URL from Render
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# --- Models ---
class Record(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    gate = db.Column(db.String, nullable=False)
    timestamp = db.Column(db.String, nullable=False)  # keep as text for now
    fishid = db.Column(db.String, nullable=False)
    logfile = db.Column(db.String, nullable=False)

class Import(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String, unique=True, nullable=False)
    imported_on = db.Column(db.String, nullable=False)

# Create tables automatically
with app.app_context():
    db.create_all()

@app.route("/")
def index():
    return render_template("index.html")

@app.post("/api/upload")
def api_upload():
    if "files" not in request.files:
        return jsonify({"error": "No files uploaded"}), 400

    files = request.files.getlist("files")
    total_added, total_dummy = 0, 0
    details = []

    for f in files:
        fname = f.filename
        lines = f.read().decode("utf-8", errors="ignore").splitlines()

        dummy_count, added_count = 0, 0
        batch = []

        for line in lines:
            if not line.startswith("TAG"):
                continue
            parts = line.split()
            if len(parts) < 6:
                continue
            gate, ts, fish = parts[2], parts[3] + " " + parts[4], parts[5]
            tag_end = fish[-3:]
            if "D01" <= tag_end <= "D07":
                dummy_count += 1
                continue
            batch.append(Record(gate=gate, timestamp=ts, fishid=fish, logfile=fname))

        # sort by fishid then timestamp
        batch.sort(key=lambda r: (r.fishid, r.timestamp))

        # remove in-between duplicates
        cleaned, i = [], 0
        while i < len(batch):
            start, fid, g = i, batch[i].fishid, batch[i].gate
            i += 1
            while i < len(batch) and batch[i].fishid == fid and batch[i].gate == g:
                i += 1
            run = batch[start:i]
            if len(run) >= 3:
                cleaned.append(run[0])  # keep first
                cleaned.append(run[-1]) # keep last
            else:
                cleaned.extend(run)

        if cleaned:
            db.session.add_all(cleaned)
            added_count = len(cleaned)

        total_dummy += dummy_count
        total_added += added_count
        details.append({"file": fname, "added": added_count, "dummy_removed": dummy_count})

        # record import
        imp = Import(filename=fname, imported_on=str(date.today()))
        db.session.merge(imp)  # upsert

    db.session.commit()
    return jsonify({"summary": {"total_added": total_added, "total_dummy_removed": total_dummy}, "details": details})

@app.get("/api/records")
def api_records():
    rows = Record.query.limit(1000).all()
    return jsonify([{"gate": r.gate, "timestamp": r.timestamp, "fishid": r.fishid, "logfile": r.logfile} for r in rows])

@app.get("/api/counts")
def api_counts():
    total = db.session.query(func.count(Record.id)).scalar()
    unique_fish = db.session.query(func.count(func.distinct(Record.fishid))).scalar()
    return jsonify({"antenna_hits": total, "unique_fish": unique_fish})

@app.get("/api/imports")
def api_imports():
    rows = Import.query.all()
    return jsonify([{"filename": r.filename, "imported_on": r.imported_on} for r in rows])

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
