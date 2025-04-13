📁 HỆ THỐNG CHIA SẺ FILE P2P – HƯỚNG DẪN CHẠY
────────────────────────────────────────────

I. 📦 THÀNH PHẦN FILE

| Tên tệp                | Mục đích                                      |
| ---------------------- | --------------------------------------------- |
| tracker_full_server.py | Tracker Flask lưu Peer và xác thực người dùng |
| peer.py                | Seeder riêng: chia sẻ file                    |

II. 🛠 CÀI ĐẶT

Yêu cầu:

- Python >= 3.9
- Các thư viện:
  pip install flask requests

Cấu trúc thư mục:

- shared/: chứa file hoặc thư mục chia sẻ
- torrents/: chứa file .torrent đã tạo
- downloads/: chứa file tải về từ các peer
- downloads/.progress/: lưu tiến trình tải dở

III. 🚀 CÁCH CHẠY HỆ THỐNG

1. 🔗 CHẠY TRACKER SERVER

   - Trên máy chủ:
     python tracker_full_server.py
   - Tracker lắng nghe tại http://<IP>:5000

2. 🧑 ĐĂNG KÝ TÀI KHOẢN (qua API hoặc Thunder Client)

   - POST /register
   - Body:
     {
     "username": "user1",
     "password": "123456"
     }

3. 📡 CHẠY SEEDER
   - Chia sẻ file:
     python peer.py
     Nhập đường dẫn file .torrent
   - Tải file:
     python peer.py
     Chọn file muốn tải

IV. 🔁 TÍNH NĂNG RESUME

- Tự lưu tiến trình mỗi piece vào downloads/.progress/
- Nếu quá trình bị ngắt, sẽ tiếp tục từ nơi đã dừng

V. 🌐 TRIỂN KHAI NHIỀU MÁY

- Tracker chạy tại 1 máy cố định (ví dụ: 192.168.1.88)
- Peer nhập IP tracker khi chạy CLI
- Đảm bảo:
  - Cổng 5000 (tracker) mở
  - Cổng 6881 (peer) không bị chặn bởi firewall

────────────────────────────────────────────
✅ Hệ thống hỗ trợ đăng nhập, đa peer, đa file, resume
📡 Kết nối tracker trung tâm, tải file song song từ nhiều peer
✨ Giao diện CLI đơn giản, dễ triển khai trên mạng LAN
