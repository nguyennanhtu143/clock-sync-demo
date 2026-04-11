# Giải thích cách hoạt động — Server Side

Folder `server/` chứa 3 file Python chạy trên **1 máy Server (Node 0)**. Khi bạn chạy `python dashboard.py`, cả 3 component đều khởi động cùng lúc trong các thread riêng biệt.

---

## Tổng quan kiến trúc

```
python dashboard.py
       │
       ├── Thread 1: ntp_server.py    →  lắng nghe Port 5000  (TCP)
       │                                 ← nhận NTP request từ các Client
       │
       ├── Thread 2: logic_server.py  →  lắng nghe Port 5001  (TCP)
       │                                 ← nhận/forward sự kiện Logical Clock
       │
       └── Main Thread: dashboard.py  →  chạy Web Flask  Port 8080  (HTTP)
                                         ← nhận report từ Client qua REST API
                                         → push dữ liệu ra browser qua SocketIO
```

---

## 1. `ntp_server.py` — NTP Time Server

### Vai trò
Đây là **"Master Clock"** (đồng hồ gốc). Thời gian của máy Server được coi là chuẩn, tất cả Client sẽ đồng bộ về thời gian này.

### Cách hoạt động

**Khởi động:**
- Mở một TCP socket, bind vào `0.0.0.0:5000` (nhận kết nối từ mọi IP).
- Vòng lặp `while True` chờ Client kết nối.
- Mỗi Client kết nối vào sẽ được xử lý trong một **thread riêng** (`threading.Thread`) để Server phục vụ nhiều Client cùng lúc.

**Khi có Client kết nối (`handle_client`):**

```
Client gửi JSON:  { "node_id": 1, "T1": 1712644580.123 }
                                  ↑
                           T1 là thời gian Client ghi lại lúc gửi

Server nhận → ghi T2 = time.time()   ← thời điểm server nhận được
Server ngủ 50ms  ← time.sleep(0.05)  ← mô phỏng processing delay
Server ghi T3 = time.time()          ← thời điểm server chuẩn bị gửi

Server gửi JSON:  { "T2": ..., "T3": ... }
```

**Tại sao lại có `time.sleep(0.05)`?**
Trong NTP thực tế, server mất một ít thời gian xử lý request. `T2` và `T3` phải khác nhau (T3 > T2) để công thức tính delay chính xác hơn. Nếu T2 ≈ T3 thì không mô phỏng được thực tế.

**Lưu kết quả:**
Sau mỗi lần phục vụ Client, server lưu dữ liệu `{node_id, ip, T1, T2, T3}` vào biến `ntp_results` (dùng `threading.Lock` để tránh race condition giữa các thread).

---

## 2. `logic_server.py` — Logical Clock Coordinator

### Vai trò
Đây là **"Bưu cục trung tâm"**. Khi Node A muốn gửi message cho Node B, Node A không gửi thẳng cho Node B mà gửi lên Server. Server sẽ forward về Node B.

### Tại sao phải qua Server?
Trong ví dụ này, mỗi Client chỉ kết nối vào Server chứ không kết nối trực tiếp với nhau. Server giữ một bảng `node_connections = {node_id: socket_conn}` để biết socket của từng Client, từ đó có thể forward message đến đúng người nhận.

### Cách hoạt động

**Khởi động:**
- Mở TCP socket bind vào `0.0.0.0:5001`.
- Mỗi Client kết nối được xử lý trong 1 thread riêng.
- Server dùng kỹ thuật **line-buffered protocol**: mỗi message JSON kết thúc bằng `\n`, nên nhiều message có thể gộp trong 1 lần `recv()` và server tách chúng ra bằng ký tự newline.

**Khi nhận message từ Client:**

| Loại message (`type`) | Hành động của Server |
|---|---|
| `register` | Lưu `node_id → socket` vào `node_connections`. Gửi lại `{"type": "registered"}` để xác nhận. |
| `local_event` | Log ra console + gọi `record_event()` → lưu vào `logic_events` **và emit SocketIO real-time**. |
| `send_event` | Log + lưu. **Quan trọng:** Lấy socket của `target_node` từ `node_connections`, gửi `{"type": "receive_event", ...}` đến node đích. |
| `receive_ack` | Client gửi lên sau khi đã xử lý message nhận được. Server log + lưu sự kiện RECEIVE. |

**`record_event()` — hàm trung tâm:**
Mọi loại sự kiện đều đi qua hàm này. Nó làm 2 việc:
1. Append vào danh sách `logic_events` (có lock)
2. Gọi `_emit_callback("logic_update", event)` nếu callback đã được đăng ký bởi dashboard

```python
def record_event(event_data):
    with logic_lock:
        logic_events.append(event_data)        # lưu vào danh sách
    if _emit_callback:
        _emit_callback("logic_update", event_data)  # push real-time đến browser
```

**Khi Client ngắt kết nối:**
- Xóa node đó khỏi `connected_nodes` và `node_connections`.

---

## 3. `dashboard.py` — Web Dashboard

### Vai trò
Là **giao diện điều khiển trực quan**. Tổng hợp dữ liệu từ cả 2 server và đẩy lên browser real-time.

### Cách hoạt động

**Khởi động (`__main__`):**
1. Gọi `start_ntp_server_thread()` → import `ntp_server.py`, gọi `start_server()` trong 1 daemon thread.
2. Gọi `start_logic_server_thread()` → import `logic_server` dưới dạng **module object**, đăng ký `socketio.emit` làm callback, sau đó mới chạy `start_server()` trong daemon thread.
3. Chạy Flask + SocketIO trên thread chính, Port 8080.

**Tại sao phải đăng ký callback?**

`logic_server.py` và `dashboard.py` chạy trong cùng 1 Python process nhưng có **biến module riêng biệt**. Nếu để logic_server tự gọi `socketio.emit`, nó phải import dashboard → tạo circular import. Giải pháp là dùng **callback injection**: dashboard truyền `socketio.emit` vào logic_server qua `set_emit_callback()`, logic_server giữ tham chiếu hàm này và gọi khi cần:

```
# dashboard.py khi khởi động:
import logic_server as ls
ls.set_emit_callback(socketio.emit)   ← inject SocketIO vào logic_server

# logic_server.py khi có sự kiện mới:
_emit_callback("logic_update", event)  ← gọi socketio.emit mà không biết dashboard là gì
```

**REST API endpoints:**

| Endpoint | Method | Mô tả |
|---|---|---|
| `GET /` | GET | Trả về trang HTML dashboard (`templates/index.html`) |
| `POST /api/ntp/result` | POST | **Client gửi kết quả NTP lên đây sau khi sync xong.** Dashboard lưu vào `ntp_results` và broadcast SocketIO event `ntp_update`. |
| `POST /api/logic/event` | POST | Nhận sự kiện Logic Clock (dự phòng, hiện chưa dùng). |
| `GET /api/ntp/results` | GET | Trả về JSON toàn bộ kết quả NTP (dùng để load lại khi mở browser). |
| `GET /api/logic/events` | GET | Đọc thẳng từ `logic_server.get_logic_events()` — danh sách do logic_server quản lý. |
| `GET /api/status` | GET | Trả về overview: server time, uptime, số node đã sync. |

**Luồng dữ liệu NTP đến Dashboard:**
```
NTP Client (máy client)
    │
    │  HTTP POST /api/ntp/result
    │  { node_id, T1, T2, T3, T4, delay, offset, ... }
    ▼
dashboard.py  →  lưu vào ntp_results{}
    │
    │  socketio.emit("ntp_update", ...)
    ▼
Browser (đang mở http://<IP>:8080)
    └─ dashboard.js nhận event → cập nhật biểu đồ, bảng kết quả
```

**Luồng dữ liệu Logical Clock đến Dashboard:**
```
Logic Client (máy client)
    │
    │  TCP local_event / send_event / receive_ack
    ▼
logic_server.py  →  record_event()
    │                    ├─ lưu vào logic_events[]
    │                    └─ gọi _emit_callback()  ← là socketio.emit() được inject từ dashboard
    ▼
Browser (đang mở http://<IP>:8080)
    └─ dashboard.js nhận "logic_update" → cập nhật timeline, bảng sự kiện
```

**SocketIO (real-time):**
Thay vì browser phải tự refresh trang mỗi vài giây, Flask-SocketIO duy trì một kết nối WebSocket liên tục giữa server và browser. Mỗi khi có sự kiện (NTP hoặc Logic), server ngạy lập tức push xuống browser — không cần browser hỏi lại.

---

## Luồng tổng thể khi chạy demo NTP

```
[1] Server khởi động: dashboard.py
        → NTP Server lắng nghe :5000
        → Logic Server lắng nghe :5001 + đăng ký emit callback
        → Flask Web lắng nghe :8080

[2] Thầy/cô mở browser vào http://<IP>:8080
        → Browser kết nối SocketIO, dashboard hiển thị trống

[3] Client 1 chạy ntp_client.py → kết nối TCP đến :5000
        → NTP Exchange (T1, T2, T3, T4)
        → Client tính offset và delay
        → Client HTTP POST kết quả lên /api/ntp/result

[4] dashboard.py nhận POST → lưu → SocketIO emit “ntp_update”

[5] Browser tự động cập nhật: biểu đồ + bảng kết quả hiện ra

[6] Client chạy logic_client.py → kết nối TCP đến :5001
        → Tạo sự kiện (local / send / receive)

[7] logic_server.py nhận và gọi record_event()
        → Lưu vào logic_events[]
        → Gọi _emit_callback() → socketio.emit(“logic_update”)

[8] Browser tự động cập nhật: timeline + bảng sự kiện hiện ra
```

---

## Quản lý đa luồng (Threading)

Server dùng 3 loại thread:

| Thread | Tạo bởi | Tồn tại | Mục đích |
|---|---|---|---|
| NTP worker | `threading.Thread` trong `start_server()` | Chỉ trong lúc phục vụ 1 request | Xử lý 1 Client NTP |
| Logic worker | `threading.Thread` trong `start_server()` | Tồn tại liên tục khi Client kết nối | Giữ kết nối và xử lý nhiều event |
| Dashboard listener | `_listen_incoming()` trong LogicClient | Suốt quá trình chạy | Nhận message forward từ server |

Tất cả thread dùng `daemon=True`, nghĩa là chúng tự tắt khi chương trình chính kết thúc, không cần xử lý cleanup thủ công.

Mọi biến dùng chung giữa nhiều thread (`ntp_results`, `logic_events`, `node_connections`) đều được bảo vệ bởi `threading.Lock()` để tránh race condition.
