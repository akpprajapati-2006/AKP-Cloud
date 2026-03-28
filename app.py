from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import hashlib
from datetime import datetime
from supabase import create_client, Client

app = Flask(__name__)
CORS(app)

SUPABASE_URL = "https://mhxvfmpgquozppvnzjgz.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1oeHZmbXBncXVvenBwdm56amd6Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NDQzMDQ2OCwiZXhwIjoyMDkwMDA2NDY4fQ._RWBLNyGJn5D68NoP0_T8xFbYPgfvBBMX0BSvyPZUS0"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

UPLOAD_DIR = "user_storage"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ── REGISTER ──────────────────────────────────────────────
@app.route("/api/register", methods=["POST"])
def register():
    data = request.json
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    email = data.get("email", "").strip()

    if not username or not password:
        return jsonify({"error": "Username aur password zaroori hai"}), 400

    existing = supabase.table("users").select("username").eq("username", username).execute()
    if existing.data:
        return jsonify({"error": "Username already exists"}), 409

    supabase.table("users").insert({
        "username": username,
        "password": hash_password(password),
        "email": email,
        "created": datetime.now().isoformat()
    }).execute()

    return jsonify({"message": "Registration successful", "username": username})

# ── LOGIN ─────────────────────────────────────────────────
@app.route("/api/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    result = supabase.table("users").select("*").eq("username", username).execute()
    if not result.data:
        return jsonify({"error": "User not found"}), 404

    user = result.data[0]
    if user["password"] != hash_password(password):
        return jsonify({"error": "Incorrect password"}), 401

    return jsonify({"message": "Login successful", "username": username})

# ── FILES LIST ────────────────────────────────────────────
@app.route("/api/files/<username>", methods=["GET"])
def list_files(username):
    result = supabase.table("files").select("*").eq("username", username).execute()
    files = []
    for f in result.data:
        files.append({
            "name": f["filename"],
            "size": f.get("size", 0),
            "modified": f.get("uploaded_at", ""),
            "type": f.get("filetype", "application/octet-stream")
        })
    return jsonify({"files": files})

# ── UPLOAD ────────────────────────────────────────────────
@app.route("/api/upload/<username>", methods=["POST"])
def upload_file(username):
    if "file" not in request.files:
        return jsonify({"error": "No file"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    user_dir = os.path.join(UPLOAD_DIR, username)
    os.makedirs(user_dir, exist_ok=True)
    save_path = os.path.join(user_dir, file.filename)
    file.save(save_path)
    size = os.path.getsize(save_path)

    existing = supabase.table("files").select("id").eq("username", username).eq("filename", file.filename).execute()
    if existing.data:
        supabase.table("files").update({
            "size": size,
            "uploaded_at": datetime.now().isoformat(),
            "filetype": file.content_type
        }).eq("username", username).eq("filename", file.filename).execute()
    else:
        supabase.table("files").insert({
            "username": username,
            "filename": file.filename,
            "size": size,
            "uploaded_at": datetime.now().isoformat(),
            "filetype": file.content_type
        }).execute()

    return jsonify({"message": f"{file.filename} uploaded successfully"})

# ── DOWNLOAD ──────────────────────────────────────────────
@app.route("/api/download/<username>/<filename>", methods=["GET"])
def download_file(username, filename):
    file_path = os.path.join(UPLOAD_DIR, username, filename)
    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404
    return send_file(file_path, as_attachment=True, download_name=filename)

# ── READ ──────────────────────────────────────────────────
@app.route("/api/read/<username>/<filename>", methods=["GET"])
def read_file(username, filename):
    file_path = os.path.join(UPLOAD_DIR, username, filename)
    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return jsonify({"content": content, "filename": filename})
    except:
        return jsonify({"error": "Binary file read nahi ho sakta"}), 400

# ── WRITE ─────────────────────────────────────────────────
@app.route("/api/write/<username>/<filename>", methods=["POST"])
def write_file(username, filename):
    data = request.json
    content = data.get("content", "")
    user_dir = os.path.join(UPLOAD_DIR, username)
    os.makedirs(user_dir, exist_ok=True)
    file_path = os.path.join(user_dir, filename)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    size = os.path.getsize(file_path)
    existing = supabase.table("files").select("id").eq("username", username).eq("filename", filename).execute()
    if existing.data:
        supabase.table("files").update({
            "size": size,
            "uploaded_at": datetime.now().isoformat()
        }).eq("username", username).eq("filename", filename).execute()
    else:
        supabase.table("files").insert({
            "username": username,
            "filename": filename,
            "size": size,
            "uploaded_at": datetime.now().isoformat(),
            "filetype": "text/plain"
        }).execute()

    return jsonify({"message": f"{filename} saved successfully"})

# ── DELETE ────────────────────────────────────────────────
@app.route("/api/delete/<username>/<filename>", methods=["DELETE"])
def delete_file(username, filename):
    file_path = os.path.join(UPLOAD_DIR, username, filename)
    if os.path.exists(file_path):
        os.remove(file_path)

    supabase.table("files").delete().eq("username", username).eq("filename", filename).execute()
    return jsonify({"message": f"{filename} deleted"})

# ── STORAGE INFO ──────────────────────────────────────────
@app.route("/api/storage/<username>", methods=["GET"])
def storage_info(username):
    result = supabase.table("files").select("size").eq("username", username).execute()
    total = sum(f.get("size", 0) for f in result.data)
    count = len(result.data)
    return jsonify({"used_bytes": total, "file_count": count})

if __name__ == "__main__":
    print("🚀 CloudVault + Supabase running!")
    app.run(debug=True, port=5000)
