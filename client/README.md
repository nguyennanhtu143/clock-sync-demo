# Client Side

Chạy trên 4 máy Client (Node 1-4).

## Thành phần
- `ntp_client.py` — NTP Sync Client (kết nối Server Port 5000)
- `logic_client.py` — Logical Clock Client (kết nối Server Port 5001)

## Cài đặt

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## Chạy NTP Client

```bash
python ntp_client.py --server-ip 192.168.1.100 --node-id 1

# Tùy chọn fake offset:
python ntp_client.py --server-ip 192.168.1.100 --node-id 2 --fake-offset 5.2
```

**Tham số:**
- `--server-ip` — IP máy Server (bắt buộc)
- `--node-id` — ID node: 1, 2, 3, hoặc 4 (bắt buộc)
- `--fake-offset` — Offset giả (giây). Mặc định random [-10, +10]

## Chạy Logic Client

```bash
python logic_client.py --server-ip 192.168.1.100 --node-id 1
```

**Menu tương tác:**
1. Local Event — Tạo sự kiện nội bộ
2. Send Message — Gửi message đến node khác
3. Xem trạng thái Clock
4. Xem lịch sử sự kiện
5. Thoát
