from flask import Flask, request, jsonify, redirect
from flask_cors import CORS
import os
import hashlib
from datetime import datetime
import requests as req

app = Flask(__name__)
CORS(app)

SUPABASE_URL = "https://mhxvfmpgquozppvnzjgz.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1oeHZmbXBncXVvenBwdm56amd6Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NDQzMDQ2OCwiZXhwIjoyMDkwMDA2NDY4fQ._RWBLNyGJn5D68NoP0_T8xFbYPgfvBBMX0BSvyPZUS0"
BUCKET = "user-files"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def sb_get(table, filters=""):
    url = f"{SUPABASE_URL}/rest/v1/{table}?{filters}"
    r = req.get(url, headers=HEADERS)
    return r.json()

def sb_post(table, data):
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    r = req.post(url, headers=HEADERS, json=data)
    return r.json()

def sb_patch(table, filters, data):
    url = f"{SUPABASE_URL}/rest/v1/{table}?{filters}"
    r = req.patch(url, headers=HEADERS, json=data)
    return r.json()

def sb_delete(table, filters):
    url = f"{SUPABASE_URL}/rest/v1/{table}?{filters}"
    r = req.delete(url, headers=HEADERS)
    return r.status_code

# ── REGISTER ──────────────────────────────────────────────
@app.route("/api/register", methods=["POST"])
def register():
    data = request.json
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    email = data.get("email", "").strip()

    if not username or not password:
        return jsonify({"error": "Username aur password zaroori hai"}), 400

    existing = sb_get("users", f"username=eq.{username}&select=username")
    if isinstance(existing, list) and len(existing) > 0:
        return jsonify({"error": "Username already exists"}), 409

    sb_post("users", {
        "username": username,
        "password": hash_password(password),
        "email": email,
        "created": datetime.now().isoformat()
    })

    return jsonify({"message": "Registration successful", "username": username})

# ── LOGIN ─────────────────────────────────────────────────
@app.route("/api/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    result = sb_get("users", f"username=eq.{username}&select=*")
    if not isinstance(result, list) or len(result) == 0:
        return jsonify({"error": "User not found"}), 404

    user = result[0]
    if user["password"] != hash_password(password):
        return jsonify({"error": "Incorrect password"}), 401

    return jsonify({"message": "Login successful", "username": username})

# ── FILES LIST ────────────────────────────────────────────
@app.route("/api/files/<username>", methods=["GET"])
def list_files(username):
    result = sb_get("files", f"username=eq.{username}&select=*")
    files = []
    if isinstance(result, list):
        for f in result:
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

    file_content = file.read()
    size = len(file_content)
    storage_path = f"{username}/{file.filename}"

    # Upload to Supabase Storage
    storage_headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": file.content_type or "application/octet-stream",
        "x-upsert": "true"
    }
    storage_url = f"{SUPABASE_URL}/storage/v1/object/{BUCKET}/{storage_path}"
    req.post(storage_url, headers=storage_headers, data=file_content)

    # Save metadata in files table
    existing = sb_get("files", f"username=eq.{username}&filename=eq.{file.filename}&select=id")
    if isinstance(existing, list) and len(existing) > 0:
        sb_patch("files", f"username=eq.{username}&filename=eq.{file.filename}", {
            "size": size,
            "uploaded_at": datetime.now().isoformat(),
            "filetype": file.content_type or "application/octet-stream"
        })
    else:
        sb_post("files", {
            "username": username,
            "filename": file.filename,
            "size": size,
            "uploaded_at": datetime.now().isoformat(),
            "filetype": file.content_type or "application/octet-stream"
        })

    return jsonify({"message": f"{file.filename} uploaded successfully"})

# ── DOWNLOAD ──────────────────────────────────────────────
@app.route("/api/download/<username>/<filename>", methods=["GET"])
def download_file(username, filename):
    storage_path = f"{username}/{filename}"
    download_url = f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET}/{storage_path}"

    storage_headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    r = req.get(download_url, headers=storage_headers)

    if r.status_code == 200:
        from flask import Response
        return Response(
            r.content,
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Type": r.headers.get("Content-Type", "application/octet-stream")
            }
        )
    return jsonify({"error": "File not found"}), 404

# ── READ ──────────────────────────────────────────────────
@app.route("/api/read/<username>/<filename>", methods=["GET"])
def read_file(username, filename):
    storage_path = f"{username}/{filename}"
    download_url = f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET}/{storage_path}"

    r = req.get(download_url)
    if r.status_code == 200:
        try:
            content = r.content.decode("utf-8")
            return jsonify({"content": content, "filename": filename})
        except:
            return jsonify({"error": "Binary file read nahi ho sakta"}), 400
    return jsonify({"error": "File not found"}), 404

# ── WRITE ─────────────────────────────────────────────────
@app.route("/api/write/<username>/<filename>", methods=["POST"])
def write_file(username, filename):
    data = request.json
    content = data.get("content", "")
    file_content = content.encode("utf-8")
    size = len(file_content)
    storage_path = f"{username}/{filename}"

    storage_headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "text/plain",
        "x-upsert": "true"
    }
    storage_url = f"{SUPABASE_URL}/storage/v1/object/{BUCKET}/{storage_path}"
    req.post(storage_url, headers=storage_headers, data=file_content)

    existing = sb_get("files", f"username=eq.{username}&filename=eq.{filename}&select=id")
    if isinstance(existing, list) and len(existing) > 0:
        sb_patch("files", f"username=eq.{username}&filename=eq.{filename}", {
            "size": size,
            "uploaded_at": datetime.now().isoformat()
        })
    else:
        sb_post("files", {
            "username": username,
            "filename": filename,
            "size": size,
            "uploaded_at": datetime.now().isoformat(),
            "filetype": "text/plain"
        })

    return jsonify({"message": f"{filename} saved successfully"})

# ── DELETE ────────────────────────────────────────────────
@app.route("/api/delete/<username>/<filename>", methods=["DELETE"])
def delete_file(username, filename):
    storage_path = f"{username}/{filename}"
    storage_headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    req.delete(
        f"{SUPABASE_URL}/storage/v1/object/{BUCKET}",
        headers=storage_headers,
        json={"prefixes": [storage_path]}
    )
    sb_delete("files", f"username=eq.{username}&filename=eq.{filename}")
    return jsonify({"message": f"{filename} deleted"})

# ── STORAGE INFO ──────────────────────────────────────────
@app.route("/api/storage/<username>", methods=["GET"])
def storage_info(username):
    result = sb_get("files", f"username=eq.{username}&select=size")
    total = 0
    count = 0
    if isinstance(result, list):
        total = sum(f.get("size", 0) for f in result)
        count = len(result)
    return jsonify({"used_bytes": total, "file_count": count})

if __name__ == "__main__":
    print("CloudVault + Supabase Storage running!")
    app.run(debug=True, port=5000)
