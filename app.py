from flask import Flask, request, jsonify, send_file, after_this_request
from flask_cors import CORS
import os
import json
import hashlib
from datetime import datetime
import mimetypes

app = Flask(__name__)
CORS(app)

STORAGE_DIR = "user_storage"
USERS_FILE = "users.json"

os.makedirs(STORAGE_DIR, exist_ok=True)

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def get_user_dir(username):
    path = os.path.join(STORAGE_DIR, username)
    os.makedirs(path, exist_ok=True)
    return path

# ─── AUTH ROUTES ─────────────────────────────────────────────────────────────

@app.route("/api/register", methods=["POST"])
def register():
    data = request.json
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    email = data.get("email", "").strip()

    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400

    users = load_users()
    if username in users:
        return jsonify({"error": "Username already exists"}), 409

    users[username] = {
        "password": hash_password(password),
        "email": email,
        "created": datetime.now().isoformat()
    }
    save_users(users)
    get_user_dir(username)
    return jsonify({"message": "Registration successful", "username": username})

@app.route("/api/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    users = load_users()
    if username not in users:
        return jsonify({"error": "User not found"}), 404
    if users[username]["password"] != hash_password(password):
        return jsonify({"error": "Incorrect password"}), 401

    return jsonify({"message": "Login successful", "username": username})

# ─── FILE ROUTES ──────────────────────────────────────────────────────────────

@app.route("/api/files/<username>", methods=["GET"])
def list_files(username):
    user_dir = get_user_dir(username)
    files = []
    for fname in os.listdir(user_dir):
        fpath = os.path.join(user_dir, fname)
        stat = os.stat(fpath)
        mime, _ = mimetypes.guess_type(fname)
        files.append({
            "name": fname,
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "type": mime or "application/octet-stream"
        })
    files.sort(key=lambda x: x["modified"], reverse=True)
    return jsonify({"files": files})

@app.route("/api/upload/<username>", methods=["POST"])
def upload_file(username):
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    user_dir = get_user_dir(username)
    save_path = os.path.join(user_dir, file.filename)
    file.save(save_path)
    return jsonify({"message": f"{file.filename} uploaded successfully"})

@app.route("/api/download/<username>/<filename>", methods=["GET"])
def download_file(username, filename):
    user_dir = get_user_dir(username)
    file_path = os.path.join(user_dir, filename)
    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404
    return send_file(file_path, as_attachment=True, download_name=filename)

@app.route("/api/read/<username>/<filename>", methods=["GET"])
def read_file(username, filename):
    user_dir = get_user_dir(username)
    file_path = os.path.join(user_dir, filename)
    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return jsonify({"content": content, "filename": filename})
    except Exception:
        return jsonify({"error": "Cannot read binary file as text"}), 400

@app.route("/api/write/<username>/<filename>", methods=["POST"])
def write_file(username, filename):
    data = request.json
    content = data.get("content", "")
    user_dir = get_user_dir(username)
    file_path = os.path.join(user_dir, filename)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    return jsonify({"message": f"{filename} saved successfully"})

@app.route("/api/delete/<username>/<filename>", methods=["DELETE"])
def delete_file(username, filename):
    user_dir = get_user_dir(username)
    file_path = os.path.join(user_dir, filename)
    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404
    os.remove(file_path)
    return jsonify({"message": f"{filename} deleted"})

@app.route("/api/storage/<username>", methods=["GET"])
def storage_info(username):
    user_dir = get_user_dir(username)
    total = sum(
        os.path.getsize(os.path.join(user_dir, f))
        for f in os.listdir(user_dir)
        if os.path.isfile(os.path.join(user_dir, f))
    )
    count = len(os.listdir(user_dir))
    return jsonify({"used_bytes": total, "file_count": count})

if __name__ == "__main__":
    print("🚀 CloudVault Backend running at http://localhost:5000")
    app.run(debug=True, port=5000)