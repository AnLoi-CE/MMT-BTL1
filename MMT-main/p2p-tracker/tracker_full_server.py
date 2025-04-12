from flask import Flask, request, jsonify, send_file
import sqlite3
import hashlib
import secrets
import os
import json
import io
from collections import defaultdict
from datetime import datetime, timezone


# Cấu hình thư mục lưu trữ
TRACKER_TORRENT_FOLDER = "tracker_torrents"
os.makedirs(TRACKER_TORRENT_FOLDER, exist_ok=True)

# Tạo Flask app
app = Flask(__name__)
DB_FILE = "users.db"
torrents = defaultdict(list)  # Lưu thông tin các peer theo info_hash
stats = defaultdict(lambda: {"uploads": {}, "downloads": {}})  # Thống kê uploads và downloads

# Hàm khởi tạo cơ sở dữ liệu
def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                token TEXT
            )
        """)
        conn.commit()

# Hàm hỗ trợ
def hash_password(password): return hashlib.sha256(password.encode()).hexdigest()
def generate_token(): return secrets.token_hex(16)

def get_user_id_by_token(token):
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("SELECT id FROM users WHERE token=?", (token,))
        r = c.fetchone()
        return r[0] if r else None

# API Endpoints
#AUTH
@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    username, password = data.get("username"), data.get("password")
    if not username or not password:
        return jsonify({"error": "Thiếu thông tin"}), 400
    try:
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()
            c.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, hash_password(password)))
            conn.commit()
        return jsonify({"message": "Đăng ký thành công"}), 201
    except sqlite3.IntegrityError:
        return jsonify({"error": "Tài khoản đã tồn tại"}), 409

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    username, password = data.get("username"), data.get("password")
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("SELECT id FROM users WHERE username=? AND password_hash=?", (username, hash_password(password)))
        user = c.fetchone()
        if user:
            token = generate_token()
            c.execute("UPDATE users SET token=? WHERE id=?", (token, user[0]))
            conn.commit()
            return jsonify({"token": token}), 200
        return jsonify({"error": "Sai thông tin"}), 401

#TORRENT
@app.route("/upload_torrent", methods=["POST"])
def upload_torrent():
    data = request.get_json()
    token = data.get("token")
    user_id = get_user_id_by_token(token)
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    info_hash = data.get("info_hash")
    torrent_info = data.get("info")
    if not info_hash or not torrent_info:
        return jsonify({"error": "Thiếu thông tin info_hash hoặc info"}), 400

    folder_name = torrent_info.get("folder_name", info_hash)
    torrent_file_name = f"{folder_name}.torrent"
    torrent_file_path = os.path.join(TRACKER_TORRENT_FOLDER, torrent_file_name)

    if os.path.exists(torrent_file_path):
        return jsonify({"error": "Torrent đã tồn tại"}), 409

    try:
        with open(torrent_file_path, "w") as f:
            json.dump(data, f, indent=4)
        return jsonify({"message": "Tải torrent lên thành công", "file_path": torrent_file_path}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/list_torrents", methods=["GET"])
def list_torrents():
    try:
        torrents = []
        for file_name in os.listdir(TRACKER_TORRENT_FOLDER):
            if file_name.endswith(".torrent"):
                torrent_path = os.path.join(TRACKER_TORRENT_FOLDER, file_name)
                try:
                    with open(torrent_path, "r") as f:
                        torrent_data = json.load(f)
                    torrents.append({
                        "name": file_name,
                        "info_hash": torrent_data.get("info_hash"),
                        "folder_name": torrent_data.get("info", {}).get("folder_name")
                    })
                except json.JSONDecodeError:
                    continue
        return jsonify({"torrents": torrents}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/download_torrent", methods=["GET"])
def download_torrent():
    name = request.args.get("name")
    if not name:
        return jsonify({"error": "Tên torrent không được cung cấp"}), 400

    torrent_path = os.path.join(TRACKER_TORRENT_FOLDER, name)
    if not os.path.exists(torrent_path):
        return jsonify({"error": "Không tìm thấy torrent"}), 404

    try:
        with open(torrent_path, "rb") as f:
            return send_file(io.BytesIO(f.read()), download_name=name, as_attachment=True)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

#QUản lý peer
@app.route("/announce", methods=["POST"])
def announce():
    data = request.get_json()
    info_hash = data.get("info_hash")
    status = data.get("status")  # Trạng thái: "leecher" hoặc "seeder"
    peer_info = {
        "ip": request.remote_addr,
        "port": data.get("port"),
        "status": status,
        "last_seen": datetime.now(timezone.utc).isoformat()
    }

    if not info_hash or not peer_info["port"] or not status:
        return jsonify({"error": "Thiếu thông tin info_hash, port hoặc status"}), 400

    # Khởi tạo danh sách peer nếu chưa tồn tại
    if info_hash not in torrents:
        torrents[info_hash] = []

    # Cập nhật hoặc thêm peer
    updated = False
    for peer in torrents[info_hash]:
        if peer["ip"] == peer_info["ip"] and peer["port"] == peer_info["port"]:
            peer.update(peer_info)  # Cập nhật thông tin nếu peer đã tồn tại
            updated = True
            break

    if not updated:
        torrents[info_hash].append(peer_info)  # Thêm peer mới nếu chưa tồn tại

    return jsonify({"message": "Ghi nhận peer thành công"}), 200

@app.route("/stat", methods=["GET"])
def stat():
    all_stats = []
    for info_hash, peers in torrents.items():
        peer_list = [
            {
                "ip": peer["ip"],
                "port": peer["port"],
                "status": peer["status"],
                "last_seen": peer["last_seen"],
            }
            for peer in peers
        ]
        all_stats.append({
            "info_hash": info_hash,
            "peers": peer_list,
        })

    return jsonify(all_stats), 200

@app.route("/peers", methods=["GET"])
def get_peers():
    info_hash = request.args.get("info_hash")

    if not info_hash:
        return jsonify({"error": "Thiếu tham số info_hash"}), 400

    # Kiểm tra nếu info_hash có tồn tại trong tracker
    if info_hash not in torrents:
        return jsonify({"error": "info_hash không tồn tại"}), 404

    # Trả về danh sách các peer cho info_hash
    peers = [
        {
            "ip": peer["ip"],
            "port": peer["port"],
            "status": peer["status"],
            "last_seen": peer["last_seen"],
        }
        for peer in torrents[info_hash]
    ]

    return jsonify({"peers": peers}), 200


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000)