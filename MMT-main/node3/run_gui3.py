import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading, os, json, requests, socket, hashlib, random

TRACKER_URL = ""
TOKEN = ""
PIECE_LENGTH = 1024
SHARED_FOLDER = "shared"
TORRENT_FOLDER = "torrents"
DOWNLOAD_FOLDER = "downloads"
PROGRESS_FOLDER = os.path.join(DOWNLOAD_FOLDER, ".progress")

def sha1(data): return hashlib.sha1(data).hexdigest()
def ensure_dirs(): 
    for f in [SHARED_FOLDER, TORRENT_FOLDER, DOWNLOAD_FOLDER, PROGRESS_FOLDER]:
        os.makedirs(f, exist_ok=True)

def save_progress(info_hash, bitmap):
    with open(os.path.join(PROGRESS_FOLDER, f"{info_hash}.progress"), "w") as f:
        json.dump(bitmap, f)

def load_progress(info_hash, total):
    path = os.path.join(PROGRESS_FOLDER, f"{info_hash}.progress")
    return json.load(open(path)) if os.path.exists(path) else [False] * total

class P2PGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("🌐 P2P File Sharing")
        self.geometry("520x460")
        ensure_dirs()
        self.create_widgets()

    def create_widgets(self):
        tk.Label(self, text="Tracker URL:").pack()
        self.entry_tracker = tk.Entry(self, width=50)
        self.entry_tracker.insert(0, "http://localhost:5000")
        self.entry_tracker.pack()

        tk.Label(self, text="Username:").pack()
        self.entry_user = tk.Entry(self, width=30)
        self.entry_user.pack()

        tk.Label(self, text="Password:").pack()
        self.entry_pass = tk.Entry(self, show="*", width=30)
        self.entry_pass.pack()

        self.btn_login = tk.Button(self, text="🔐 Đăng nhập", command=self.login)
        self.btn_login.pack(pady=5)

        self.btn_upload = tk.Button(self, text="📤 Upload Thư mục", command=self.upload_folder, state="disabled")
        self.btn_upload.pack(pady=5)

        self.btn_download = tk.Button(self, text="📥 Download từ .torrent", command=self.download_torrent, state="disabled")
        self.btn_download.pack(pady=5)

        self.btn_search = tk.Button(self, text="🔍 Tìm Torrent", command=self.search_torrent, state="disabled")
        self.btn_search.pack(pady=5)

        self.status = tk.Label(self, text="⚠️ Chưa đăng nhập", fg="blue")
        self.status.pack(pady=10)

        self.progress = ttk.Progressbar(self, length=320, mode='determinate')
        self.progress.pack(pady=5)
        

    def login(self):
        global TRACKER_URL, TOKEN
        TRACKER_URL = self.entry_tracker.get().strip()
        user, pw = self.entry_user.get().strip(), self.entry_pass.get().strip()
        try:
            r = requests.post(f"{TRACKER_URL}/login", json={"username": user, "password": pw})
            if r.status_code == 200:
                TOKEN = r.json()["token"]
                self.status.config(text="✅ Đăng nhập thành công", fg="green")
                self.btn_upload.config(state="normal")
                self.btn_download.config(state="normal")
                self.btn_search.config(state="normal")
            else:
                self.status.config(text="❌ Sai thông tin", fg="red")
        except Exception as e:
            self.status.config(text=f"❌ Lỗi: {e}", fg="red")

    def upload_folder(self):
        folder = filedialog.askdirectory(initialdir=SHARED_FOLDER)
        if not folder: return
        folder_name = os.path.basename(folder)
        pieces, files, buffer = [], [], b""
        for root, _, fnames in os.walk(folder):
            for name in fnames:
                abs_path = os.path.join(root, name)
                rel_path = os.path.relpath(abs_path, folder).replace("\\", "/")
                files.append({"path": rel_path, "length": os.path.getsize(abs_path)})
                with open(abs_path, "rb") as f:
                    while chunk := f.read(4096):
                        buffer += chunk
                        while len(buffer) >= PIECE_LENGTH:
                            pieces.append(sha1(buffer[:PIECE_LENGTH]))
                            buffer = buffer[PIECE_LENGTH:]
        if buffer: pieces.append(sha1(buffer))

        info = {"folder_name": folder_name, "piece_length": PIECE_LENGTH, "files": files, "pieces": pieces}
        info_hash = sha1(json.dumps(info, sort_keys=True).encode())
        torrent = {"info_hash": info_hash, "tracker_url": TRACKER_URL, "info": info}
        with open(os.path.join(TORRENT_FOLDER, folder_name + ".torrent"), "w") as f:
            json.dump(torrent, f, indent=4)
        messagebox.showinfo("✅ Upload", f"Tạo torrent {folder_name}.torrent thành công.")

        # Tải tệp torrent lên tracker
        self.upload_torrent_to_tracker(torrent)

        threading.Thread(target=self.run_seeder, args=(torrent, folder), daemon=True).start()

    def upload_torrent_to_tracker(self, torrent):
        """
        Gửi file .torrent đến tracker qua API.
        """
        try:
            torrent["token"] = TOKEN
            headers = {"Content-Type": "application/json"}
            response = requests.post(f"{TRACKER_URL}/upload_torrent", json=torrent, headers=headers)
            if response.status_code == 200:
                messagebox.showinfo("✅ Upload", f"Tải torrent lên tracker thành công: {response.json()['file_path']}")
            elif response.status_code == 409:
                messagebox.showwarning("⚠️ Torrent tồn tại", "Torrent đã được lưu trên tracker.")
            else:
                messagebox.showerror("❌ Lỗi", f"Lỗi từ tracker: {response.json().get('error', 'Không rõ lỗi')}")
        except Exception as e:
            messagebox.showerror("❌ Lỗi", f"Lỗi khi gửi torrent lên tracker: {e}")

    def search_torrent(self):
        """
        Lấy danh sách torrent từ tracker và cho phép người dùng chọn để tải.
        """
        try:
            response = requests.get(f"{TRACKER_URL}/list_torrents")
            if response.status_code != 200:
                messagebox.showerror("❌ Lỗi", "Không thể lấy danh sách torrent từ tracker.")
                return

            torrents = response.json().get("torrents", [])
            if not torrents:
                messagebox.showinfo("🔍 Kết quả", "Không có torrent nào trên tracker.")
                return

            # Hiển thị danh sách torrent
            list_window = tk.Toplevel(self)
            list_window.title("Danh sách torrent")
            list_window.geometry("500x300")

            lb = tk.Listbox(list_window, width=70, height=15)
            lb.pack(pady=10)
            for torrent in torrents:
                lb.insert(tk.END, f"{torrent['folder_name']} ({torrent['name']})")

            def select_torrent():
                selected_index = lb.curselection()
                if not selected_index:
                    messagebox.showwarning("⚠️", "Chưa chọn torrent nào.")
                    return

                selected_torrent = torrents[selected_index[0]]
                list_window.destroy()
                self.download_selected_torrent(selected_torrent)

            tk.Button(list_window, text="Chọn", command=select_torrent).pack()

        except Exception as e:
            messagebox.showerror("❌ Lỗi", f"Lỗi khi tìm torrent: {e}")


    def download_selected_torrent(self, torrent):
        """
        Tải tệp torrent được chọn từ tracker và bắt đầu tải xuống.
        """
        try:
            torrent_name = torrent["name"]
            response = requests.get(f"{TRACKER_URL}/download_torrent", params={"name": torrent_name})
            if response.status_code != 200:
                messagebox.showerror("❌ Lỗi", "Không thể tải torrent từ tracker.")
                return

            # Lưu file torrent vào thư mục
            torrent_path = os.path.join(TORRENT_FOLDER, torrent_name)
            with open(torrent_path, "wb") as f:
                f.write(response.content)

            messagebox.showinfo("✅ Thành công", f"Tải torrent {torrent_name} thành công.")
            self.download_torrent_from_path(torrent_path)

        except Exception as e:
            messagebox.showerror("❌ Lỗi", f"Lỗi khi tải torrent: {e}")

    def run_seeder(self, torrent, folder):
        info = torrent["info"]
        info_hash = torrent["info_hash"]
        buffer, data, i = b"", {}, 0
        for f in info["files"]:
            path = os.path.join(folder, f["path"])
            with open(path, "rb") as fobj:
                while chunk := fobj.read(4096):
                    buffer += chunk
                    while len(buffer) >= info["piece_length"]:
                        data[i] = buffer[:info["piece_length"]]
                        buffer = buffer[info["piece_length"]:]
                        i += 1
        if buffer: data[i] = buffer

        port = random.randint(10000, 60000)
        requests.post(
            f"{TRACKER_URL}/announce",
            json={
                "info_hash": info_hash,
                "peer_id": "peer1",
                "ip": "127.0.0.1",
                "port": port,
                "status": "seeder",  # Trạng thái của seeder
                "event": "started",
                "token": TOKEN,
            }
        )

        def handle(conn, addr):
            try:
                msg = conn.recv(1024).decode()
                h, idx = msg.split("|")
                conn.sendall(data.get(int(idx), b"NOT_FOUND"))
            finally: conn.close()

        s = socket.socket(); s.bind(("0.0.0.0", port)); s.listen(5)
        while True: threading.Thread(target=handle, args=s.accept()).start()
    
    def download_torrent(self):
        torrent_path = filedialog.askopenfilename(initialdir=TORRENT_FOLDER)
        if not torrent_path: return
        with open(torrent_path) as f:
            torrent = json.load(f)
        info = torrent["info"]
        info_hash = torrent["info_hash"]
        pieces, folder = info["pieces"], info["folder_name"]
        peers = requests.get(f"{TRACKER_URL}/peers", params={"info_hash": info_hash}).json()["peers"]
        bitmap = load_progress(info_hash, len(pieces))

        def download_piece(i):
            if bitmap[i]: return
            for peer in peers:
                try:
                    s = socket.socket(); s.connect((peer["ip"], peer["port"]))
                    s.sendall(f"{info_hash}|{i}".encode())
                    data = s.recv(PIECE_LENGTH); s.close()
                    if sha1(data) == pieces[i]:
                        with open(f"{DOWNLOAD_FOLDER}/{folder}.part{i}", "wb") as f:
                            f.write(data)
                        bitmap[i] = True
                        save_progress(info_hash, bitmap)
                        self.progress["value"] = 100 * sum(bitmap) / len(pieces)
                        return
                except: continue

        def run_download():
            threads = [threading.Thread(target=download_piece, args=(i,)) for i in range(len(pieces))]
            [t.start() for t in threads]; [t.join() for t in threads]

            if not all(bitmap):
                messagebox.showwarning("⚠️", "Một số phần chưa tải xong.")
                return

            os.makedirs(os.path.join(DOWNLOAD_FOLDER, folder), exist_ok=True)
            buffer = b""
            for i in range(len(pieces)):
                part = f"{DOWNLOAD_FOLDER}/{folder}.part{i}"
                with open(part, "rb") as f:
                    buffer += f.read()
                os.remove(part)

            offset = 0
            for fobj in info["files"]:
                out_path = os.path.join(DOWNLOAD_FOLDER, folder, fobj["path"])
                os.makedirs(os.path.dirname(out_path), exist_ok=True)
                with open(out_path, "wb") as out:
                    out.write(buffer[offset:offset + fobj["length"]])
                    offset += fobj["length"]
            messagebox.showinfo("🎉 Thành công", f"Đã tải vào: downloads/{folder}")

        threading.Thread(target=run_download, daemon=True).start()


if __name__ == "__main__":
    app = P2PGUI()
    app.mainloop()
