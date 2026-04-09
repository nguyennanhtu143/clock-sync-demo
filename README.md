# Hệ thống Đồng bộ Thời gian Phân tán

## Mô tả
Demo đồng bộ thời gian trong hệ thống phân tán trên 5 máy vật lý (1 Server + 4 Client):
- **NTP** — Đồng bộ đồng hồ vật lý
- **Lamport Clock** — Đồng hồ logic scalar
- **Vector Clock** — Đồng hồ logic vector

## Kiến trúc

```
Server (Node 0)                     Client (Node 1-4)
├── NTP Server (Port 5000)          ├── NTP Client
├── Logic Server (Port 5001)        └── Logic Client
└── Web Dashboard (Port 8080)
```

## Cài đặt & Chạy

### Trên máy Server

```bash
cd server
python -m venv venv
venv\Scripts\activate      # Windows
pip install -r requirements.txt

# Chạy tất cả (NTP + Logic + Dashboard):
python dashboard.py
```

Mở browser: `http://<IP_SERVER>:8080`

### Trên máy Client (mỗi client 1 máy)

```bash
cd client
python -m venv venv
venv\Scripts\activate      # Windows
pip install -r requirements.txt

# NTP Sync:
python ntp_client.py --server-ip <IP_SERVER> --node-id 1

# Logical Clock:
python logic_client.py --server-ip <IP_SERVER> --node-id 1
```

## Kịch bản Demo

### Demo 1: NTP (5-10 phút)
1. Server: chạy `python dashboard.py`
2. Mở dashboard: `http://<IP_SERVER>:8080`
3. 4 Client chạy: `python ntp_client.py --server-ip <IP> --node-id <1-4>`
4. Nhấn Enter trên mỗi client để sync
5. Xem kết quả console + dashboard

### Demo 2: Logical Clocks (5-10 phút)
1. Server đã chạy (từ dashboard.py)
2. 4 Client chạy: `python logic_client.py --server-ip <IP> --node-id <1-4>`
3. Tạo sự kiện qua menu tương tác
4. Xem timeline + bảng so sánh trên dashboard

## Công thức NTP
- Delay: `δ = ((T2-T1) + (T4-T3)) / 2`
- Offset: `θ = ((T2-T1) - (T4-T3)) / 2`
