from flask import Flask, request, render_template, send_file
import re, pandas as pd, os

app = Flask(__name__)
MASTER_FILE = "pit_master.csv"

# Regex to capture PIT TAG lines
tag_pattern = re.compile(r"TAG:\s+(\d+)\s+(\d+)\s+(\d+/\d+/\d+\s+\d+:\d+:\d+\.\d+)\s+([0-9A-F.]+)")

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload():
    all_records = []

    for file in request.files.getlist("files"):
        fname = file.filename
        lines = file.read().decode("utf-8").splitlines()
        for line in lines:
            match = tag_pattern.search(line)
            if match:
                gate = match.group(2)           # Node (Gate)
                timestamp = match.group(3)     # Date + Time
                fish_id = match.group(4)       # PIT Tag code
                all_records.append((timestamp, gate, fish_id, fname))

    if all_records:
        df = pd.DataFrame(all_records, columns=["timestamp", "gate", "fish_id", "file_name"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], format="%m/%d/%Y %H:%M:%S.%f")

        if os.path.exists(MASTER_FILE):
            df.to_csv(MASTER_FILE, mode="a", header=False, index=False)
        else:
            df.to_csv(MASTER_FILE, index=False)

        return f"✅ Import complete! Added {len(all_records)} detections."
    else:
        return "⚠️ No PIT tag detections found in uploaded files."

@app.route("/delete", methods=["POST"])
def delete_records():
    target_file = request.form.get("filename")

    if not os.path.exists(MASTER_FILE):
        return "⚠️ No master file found yet."

    df = pd.read_csv(MASTER_FILE, parse_dates=["timestamp"])
    before_count = len(df)

    df = df[df["file_name"] != target_file]
    after_count = len(df)

    df.to_csv(MASTER_FILE, index=False)
    deleted = before_count - after_count

    return f"🗑️ Deleted {deleted} records from {target_file}."

@app.route("/download", methods=["GET"])
def download():
    if not os.path.exists(MASTER_FILE):
        return "⚠️ No data file to download yet."
    return send_file(MASTER_FILE, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)
