# Server Side

Chạy trên 1 máy đóng vai Server (Node 0).

## Thành phần
- `ntp_server.py` — NTP Time Server (Port 5000)
- `logic_server.py` — Logical Clock Coordinator (Port 5001)
- `dashboard.py` — Web Dashboard tổng hợp (Port 8080), tự động khởi động cả NTP và Logic server

## Cài đặt

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## Chạy

```bash
# Chạy tất cả (khuyên dùng):
python dashboard.py

# Hoặc chạy riêng từng phần:
python ntp_server.py        # Chỉ NTP
python logic_server.py      # Chỉ Logic
```

## Dashboard
- URL: `http://0.0.0.0:8080`
- Tab NTP: Biểu đồ offset, delay, bảng kết quả
- Tab Logic: Space-time diagram, bảng sự kiện
- Tab So sánh: Lamport vs Vector vs NTP
