pip install requests flask

run tracker_full_server.py

Dùng API để register.

sau đó chạy node1, node2, node3

Ở đây khi mà mình đăng nhập vào sẽ dùng được các tính năng.

- Upload thư mục: Cái này phải được thực hiện để đánh dấu rằng peer này đã trở thành seeder, sẵn sàng cho các peer khác tải về

- Download từ .torrent: Cái này là torrent nội bộ trong node, Tức là phải tải torrent, mà các peer khác đã khai báo ở trên tracker trước rồi mới tiến hành tải file về được.

- Tìm Torrent: là mình lên tải torrent trên tracker xuống file nội bộ node.