from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import datetime

app = Flask(__name__)
CORS(app)

SUPABASE_URL = "https://mhxvfmpgquozppvnzjgz.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1oeHZmbXBncXVvenBwdm56amd6Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQ0MzA0NjgsImV4cCI6MjA5MDAwNjQ2OH0.JUHRANfc4aNWjgkUK1unKqGks3Qi6KwgBw7mn6MJP7Q"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

# REGISTER
@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    username = data['username']
    password = data['password']

    payload = {
        "username": username,
        "password": password,
        "created": str(datetime.datetime.now())
    }

    r = requests.post(f"{SUPABASE_URL}/rest/v1/users", json=payload, headers=HEADERS)
    return jsonify({"message": "User registered"})


# LOGIN
@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data['username']
    password = data['password']

    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/users?username=eq.{username}&password=eq.{password}",
        headers=HEADERS
    )

    if r.json():
        return jsonify({"message": "Login success"})
    else:
        return jsonify({"error": "Invalid login"}), 401


# SAVE FILE
@app.route('/api/write/<username>/<filename>', methods=['POST'])
def write_file(username, filename):
    content = request.json['content']

    payload = {
        "username": username,
        "filename": filename,
        "content": content
    }

    requests.post(f"{SUPABASE_URL}/rest/v1/files", json=payload, headers=HEADERS)
    return jsonify({"message": "Saved"})


# READ FILE
@app.route('/api/read/<username>/<filename>', methods=['GET'])
def read_file(username, filename):
    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/files?username=eq.{username}&filename=eq.{filename}",
        headers=HEADERS
    )

    data = r.json()
    if data:
        return jsonify({"content": data[0]["content"]})
    return jsonify({"error": "Not found"})


if __name__ == '__main__':
    app.run(debug=True)
