from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import datetime
import os

app = Flask(__name__)
CORS(app)

# 🔥 Supabase Config
SUPABASE_URL = "https://mhxvfmpgquozppvnzjgz.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1oeHZmbXBncXVvenBwdm56amd6Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQ0MzA0NjgsImV4cCI6MjA5MDAwNjQ2OH0.JUHRANfc4aNWjgkUK1unKqGks3Qi6KwgBw7mn6MJP7Q"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

# ✅ REGISTER
@app.route('/api/register', methods=['POST'])
def register():
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')

        # check empty
        if not username or not password:
            return jsonify({"error": "Username & Password required"}), 400

        # check user already exists
        check = requests.get(
            f"{SUPABASE_URL}/rest/v1/users",
            headers=HEADERS,
            params={"username": f"eq.{username}"}
        )

        if check.json():
            return jsonify({"error": "User already exists"}), 400

        payload = {
            "username": username,
            "password": password,
            "created": str(datetime.datetime.now())
        }

        r = requests.post(
            f"{SUPABASE_URL}/rest/v1/users",
            json=payload,
            headers=HEADERS
        )

        return jsonify({"message": "User registered successfully"})

    except Exception as e:
        return jsonify({"error": str(e)})


# ✅ LOGIN
@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')

        r = requests.get(
            f"{SUPABASE_URL}/rest/v1/users",
            headers=HEADERS,
            params={
                "username": f"eq.{username}",
                "password": f"eq.{password}"
            }
        )

        result = r.json()

        if result:
            return jsonify({"message": "Login success"})
        else:
            return jsonify({"error": "Invalid username or password"}), 401

    except Exception as e:
        return jsonify({"error": str(e)})


# ✅ SAVE FILE
@app.route('/api/write/<username>/<filename>', methods=['POST'])
def write_file(username, filename):
    try:
        content = request.json.get('content')

        payload = {
            "username": username,
            "filename": filename,
            "content": content
        }

        requests.post(
            f"{SUPABASE_URL}/rest/v1/files",
            json=payload,
            headers=HEADERS
        )

        return jsonify({"message": "File saved successfully"})

    except Exception as e:
        return jsonify({"error": str(e)})


# ✅ READ FILE
@app.route('/api/read/<username>/<filename>', methods=['GET'])
def read_file(username, filename):
    try:
        r = requests.get(
            f"{SUPABASE_URL}/rest/v1/files",
            headers=HEADERS,
            params={
                "username": f"eq.{username}",
                "filename": f"eq.{filename}"
            }
        )

        data = r.json()

        if data:
            return jsonify({"content": data[0]["content"]})
        else:
            return jsonify({"error": "File not found"}), 404

    except Exception as e:
        return jsonify({"error": str(e)})


# ✅ RUN SERVER (Render compatible)
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
