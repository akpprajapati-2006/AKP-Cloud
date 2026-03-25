from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import datetime

app = Flask(__name__)
CORS(app)

# 🔑 SUPABASE CONFIG
SUPABASE_URL = "https://mhxvfmpgquozppvnzjgz.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1oeHZmbXBncXVvenBwdm56amd6Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQ0MzA0NjgsImV4cCI6MjA5MDAwNjQ2OH0.JUHRANfc4aNWjgkUK1unKqGks3Qi6KwgBw7mn6MJP7Q"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

# =========================
# 🔐 REGISTER
# =========================
@app.route('/api/register', methods=['POST'])
def register():
    data = request.jsona

    username = data['username'].strip()
    password = data['password'].strip()

    payload = {
        "username": username,
        "password": password,
        "created": str(datetime.datetime.now())
    }

    r = requests.post(f"{SUPABASE_URL}/rest/v1/users", json=payload, headers=HEADERS)

    return jsonify({"message": "User registered"})


# =========================
# 🔑 LOGIN (FIXED)
# =========================
@app.route('/api/login', methods=['POST'])
def login():
    data = request.json

    username = data['username'].strip()
    password = data['password'].strip()

    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/users?username=eq.{username}",
        headers=HEADERS
    )

    users = r.json()

    if users and users[0]['password'] == password:
        return jsonify({"message": "Login success"})
    else:
        return jsonify({"error": "Invalid login"}), 401


# =========================
# 📁 SAVE FILE
# =========================
@app.route('/api/write/<username>/<filename>', methods=['POST'])
def write_file(username, filename):
    content = request.json['content']

    payload = {
        "username": username,
        "filename": filename,
        "content": content,
        "modified": str(datetime.datetime.now())
    }

    requests.post(f"{SUPABASE_URL}/rest/v1/files", json=payload, headers=HEADERS)

    return jsonify({"message": "Saved"})


# =========================
# 📖 READ FILE
# =========================
@app.route('/api/read/<username>/<filename>', methods=['GET'])
def read_file(username, filename):
    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/files?username=eq.{username}&filename=eq.{filename}",
        headers=HEADERS
    )

    data = r.json()

    if data:
        return jsonify({"content": data[0]["content"]})
    else:
        return jsonify({"error": "Not found"}), 404


# =========================
# 📂 LIST FILES (IMPORTANT)
# =========================
@app.route('/api/files/<username>', methods=['GET'])
def list_files(username):
    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/files?username=eq.{username}",
        headers=HEADERS
    )

    files = r.json()

    result = []
    for f in files:
        result.append({
            "name": f["filename"],
            "size": len(f.get("content", "")),
            "modified": f.get("modified", "")
        })

    return jsonify({"files": result})


# =========================
# 🗑 DELETE FILE
# =========================
@app.route('/api/delete/<username>/<filename>', methods=['DELETE'])
def delete_file(username, filename):
    requests.delete(
        f"{SUPABASE_URL}/rest/v1/files?username=eq.{username}&filename=eq.{filename}",
        headers=HEADERS
    )

    return jsonify({"message": "Deleted"})


# =========================
# 💾 STORAGE INFO
# =========================
@app.route('/api/storage/<username>', methods=['GET'])
def storage(username):
    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/files?username=eq.{username}",
        headers=HEADERS
    )

    files = r.json()

    total = sum(len(f.get("content", "")) for f in files)

    return jsonify({"used_bytes": total})


# =========================
# 🚀 RUN SERVER
# =========================
if __name__ == '__main__':
    app.run(debug=True)
