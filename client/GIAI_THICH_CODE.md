# Giải thích cách hoạt động — Client Side

Folder `client/` chứa 2 file Python chạy trên **4 máy Client (Node 1-4)**. Mỗi máy chạy độc lập, chỉ cần biết địa chỉ IP của Server và Node ID của mình.

---

## Tổng quan

```
Máy Client (Node 1, 2, 3 hoặc 4)
│
├── ntp_client.py   →  kết nối Server:5000  → đồng bộ đồng hồ vật lý (NTP)
│                   →  kết nối Server:8080  → báo kết quả lên Dashboard (HTTP)
│
└── logic_client.py →  kết nối Server:5001  → gửi/nhận sự kiện Logical Clock
```

Hai script này chạy **độc lập** (không cùng lúc). Chạy NTP trước, xong rồi mới chạy Logic.

---

## 1. `ntp_client.py` — NTP Client

### Tham số dòng lệnh

```bash
python ntp_client.py --server-ip 192.168.1.100 --node-id 1 [--fake-offset 5.2]
```

| Tham số | Bắt buộc | Mô tả |
|---|---|---|
| `--server-ip` | ✅ | IP của máy Server |
| `--node-id` | ✅ | ID node: 1, 2, 3 hoặc 4 |
| `--fake-offset` | ❌ | Độ lệch giả (giây). Nếu không truyền → random trong [-10, +10] |

### Luồng thực thi chi tiết

#### Bước 1 — Khởi tạo và hiển thị trạng thái ban đầu

Khi chạy script, `fake_offset` được sinh ra (ngẫu nhiên hoặc từ tham số). Đây là **độ lệch giả** được cộng vào thời gian OS để giả vờ rằng máy Client đang chạy lệch giờ.

```python
os_time    = time.time()              # Thời gian OS thực của máy
client_time = os_time + fake_offset   # Thời gian "bị lệch" (giả lập)
```

Console hiển thị hộp thông tin:
```
╔═══ NTP CLIENT — NODE 1 ════╗
║ Thời gian OS:   15:30:00   ║
║ Fake Offset:    +5.200s    ║
║ Thời gian Client: 15:30:05 ║  ← "nhìn thấy" 15:30:05 thay vì 15:30:00
║ Trạng thái:  ❌ CHƯA ĐỒNG BỘ ║
╚════════════════════════════╝
```

#### Bước 2 — Chờ lệnh bắt đầu

Script dừng tại `input()` và in ra:
```
⏳ Nhấn Enter để bắt đầu đồng bộ NTP...
```
Người điều phối hô "bắt đầu" → tất cả nhấn Enter cùng lúc. Điều này đảm bảo 4 Client gửi request lên Server gần như đồng thời → demo hiệu quả hơn.

#### Bước 3 — NTP Exchange (phần cốt lõi)

```
Client                              Server
  │                                   │
  │── T1 = time.time() + fake_offset  │  ← ghi T1 (thời gian "Client" gửi)
  │── send JSON { node_id, T1 } ─────►│
  │                                   │── T2 = time.time()  (server nhận)
  │                                   │── sleep(50ms)
  │                                   │── T3 = time.time()  (server gửi)
  │◄─────────── send JSON { T2, T3 } ─│
  │── T4 = time.time() + fake_offset  │  ← ghi T4 (thời gian "Client" nhận)
```

**Tại sao T1 và T4 cộng thêm `fake_offset`?**

Vì Client đang *giả vờ* rằng đồng hồ của nó bị lệch. T2 và T3 là thời gian thật của Server. Bằng cách làm T1 và T4 lệch so với thực tế, sau khi tính toán ta sẽ thu được offset ≈ `-fake_offset`, đúng với độ lệch đã cài đặt.

#### Bước 4 — Tính toán (công thức NTP)

```python
delay  = ((T2 - T1) + (T4 - T3)) / 2
offset = ((T2 - T1) - (T4 - T3)) / 2
```

**Ý nghĩa:**
- `T2 - T1`: Thời gian đi từ Client đến Server (bao gồm độ lệch đồng hồ + trễ mạng)
- `T4 - T3`: Thời gian đi từ Server về Client (bao gồm âm độ lệch đồng hồ + trễ mạng)
- **Delay (δ)**: Trung bình cộng → loại bỏ ảnh hưởng của offset, chỉ còn trễ mạng
- **Offset (θ)**: Trung bình hiệu → loại bỏ ảnh hưởng của trễ mạng, chỉ còn độ lệch đồng hồ

**Ví dụ số:**
```
fake_offset = +5.0s → T1 và T4 lớn hơn thực tế 5 giây

T1 = 15:30:05.000   (thực ra là 15:30:00, nhưng client "thấy" 15:30:05)
T2 = 15:30:00.050   (server nhận, thời gian thật)
T3 = 15:30:00.100   (server gửi)
T4 = 15:30:05.200   (thực ra là 15:30:00.200, nhưng client "thấy" 15:30:05.200)

delay  = ((0.050 - 5.000) + (5.200 - 0.100)) / 2
       = (-4.95 + 5.1) / 2 = 0.075s = 75ms  ✅ đúng với trễ thực tế

offset = ((0.050 - 5.000) - (5.200 - 0.100)) / 2
       = (-4.95 - 5.1) / 2 = -5.025s  ≈ -5.0s  ✅ đúng với fake_offset
```

#### Bước 5 — Hiển thị kết quả và áp dụng

Sau khi có `offset`, Client tính:
```python
corrected_time = time.time() + fake_offset + offset
                                ↑              ↑
                       đồng hồ bị lệch   + bù lại
               ≈ time.time()  (khớp với Server)
```

Console in kết quả rõ ràng với T1, T2, T3, T4, delay, offset và thời gian trước/sau đồng bộ.

#### Bước 6 — Báo cáo lên Dashboard

Client gửi HTTP POST đến `http://<server_ip>:8080/api/ntp/result` chứa toàn bộ thông số. Dashboard nhận và cập nhật biểu đồ real-time.

#### Bước 7 — Xác minh (30 giây)

In ra bảng so sánh mỗi giây, 30 lần:
```
[ 1/30]  Server: 15:30:00.500 | Raw: 15:30:05.500 | Synced: 15:30:00.475
[ 2/30]  Server: 15:30:01.500 | Raw: 15:30:06.500 | Synced: 15:30:01.475
...
```
- **Server**: Thời gian OS thực (chuẩn)
- **Raw**: Thời gian chưa đồng bộ (bị lệch `fake_offset`)
- **Synced**: Thời gian đã hiệu chỉnh (khớp với Server)

---

## 2. `logic_client.py` — Logical Clock Client

### Tham số dòng lệnh

```bash
python logic_client.py --server-ip 192.168.1.100 --node-id 1 [--total-nodes 5]
```

### Dữ liệu mỗi Client duy trì

```python
lamport_clock = 0                  # Một số nguyên duy nhất
vector_clock  = [0, 0, 0, 0, 0]   # Mảng 5 phần tử (1 cho mỗi node)
```

### Kết nối và đăng ký

Khi khởi động, Client kết nối TCP đến Server:5001 và gửi message đăng ký:
```json
{"type": "register", "node_id": 1, "total_nodes": 5}
```
Server gửi lại `{"type": "registered"}` xác nhận. Sau đó Client mở **1 thread listener riêng** (`_listen_incoming`) để lắng nghe các message được forward đến từ node khác — trong khi thread chính vẫn hiển thị menu cho người dùng tương tác.

### Ba loại sự kiện

#### Sự kiện LOCAL (chọn [1])
```
Người dùng nhấn [1]
    ↓
lamport_clock += 1
vector_clock[node_id] += 1
    ↓
Gửi thông báo lên Server: {"type": "local_event", lamport, vector}
    ↓
Server log + lưu vào dashboard
```

#### Sự kiện SEND (chọn [2])
```
Người dùng nhấn [2], nhập node đích (ví dụ: 2) và nội dung message
    ↓
lamport_clock += 1
vector_clock[node_id] += 1
    ↓
Gửi lên Server: {"type": "send_event", target_node: 2, lamport, vector, message}
    ↓
Server forward đến Node 2: {"type": "receive_event", from_node: 1, lamport, vector, message}
```

#### Sự kiện RECEIVE (tự động)
Thread `_listen_incoming` nhận message từ Server (forwarded từ node khác), sau đó:

```python
# Quy tắc Lamport:
lamport_clock = max(lamport_clock, received_lamport) + 1

# Quy tắc Vector:
for i in range(total_nodes):
    vector_clock[i] = max(vector_clock[i], received_vector[i])
vector_clock[node_id] += 1

# Gửi ACK lên Server:
{"type": "receive_ack", node_id, from_node, lamport, vector}
```

### Ví dụ minh họa quy tắc cập nhật

```
Trạng thái ban đầu: Node 1: LC=2, VC=[0,2,0,0,0]
                    Node 2: LC=1, VC=[0,0,1,0,0]

Node 1 gửi message cho Node 2:
  → Node 1: LC=3, VC=[0,3,0,0,0]  (sau khi tăng rồi gửi)

Node 2 nhận message từ Node 1 (lamport=3, vector=[0,3,0,0,0]):
  → Lamport: max(1, 3) + 1 = 4
  → Vector:  max([0,0,1,0,0], [0,3,0,0,0]) = [0,3,1,0,0]
             rồi index[2] += 1 → [0,3,2,0,0]
  → Node 2: LC=4, VC=[0,3,2,0,0]
```

### Phân biệt Lamport Clock và Vector Clock

| Kịch bản | Lamport | Vector Clock |
|---|---|---|
| A gửi cho B, sau đó B gửi cho C | A < B < C → phát hiện đúng thứ tự | Phát hiện đúng |
| A và B cùng gửi cho C gần như đồng thời | Lamport Clock có thể bằng nhau → không phân biệt được | VC phát hiện đây là **concurrent events** (không ai "trước" ai) |

**Concurrent events** (sự kiện đồng thời): Hai sự kiện e1 và e2 là concurrent nếu:
- `VC(e1)` không nhỏ hơn hoặc bằng `VC(e2)` theo mọi chiều
- Và ngược lại

Vector Clock là cách duy nhất để phát hiện điều này. Dashboard có phần "Concurrent Events Detection" tự động phân tích và highlight những trường hợp này.

### Menu tương tác

```
══════ LOGICAL CLOCK — NODE 1 ══════
║  [1] Local Event (sự kiện nội bộ)     ║
║  [2] Send Message → Node khác         ║
║  [3] Xem trạng thái Clock             ║
║  [4] Xem lịch sử sự kiện             ║
║  [5] Thoát                            ║
═══════════════════════════════════════
```

- **[3] Xem trạng thái**: In Lamport Clock, Vector Clock hiện tại và 5 sự kiện gần nhất.
- **[4] Xem lịch sử**: In bảng toàn bộ sự kiện với cột Lamport trước/sau và Vector trước/sau.

---

## 3. `berkeley_client.py` — Berkeley Client

### Tham số dòng lệnh

```bash
python berkeley_client.py --server-ip 192.168.1.100 --node-id 1 [--fake-offset 5.2]
```

| Tham số | Bắt buộc | Mô tả |
|---|---|---|
| `--server-ip` | ✅ | IP của máy Server (Berkeley Server Port 5002) |
| `--node-id` | ✅ | ID node: 1, 2, 3 hoặc 4 |
| `--fake-offset` | ❌ | Độ lệch giả (giây). Nếu không truyền → random trong [-10, +10] |

### Sự khác biệt cốt lõi với NTP Client

| Đặc điểm | NTP Client (Cristian) | Berkeley Client |
|---|---|---|
| Ai khởi động đồng bộ | **Client** chủ động kết nối | **Client** chờ Server gọi |
| Thời gian chạy kết nối | Ngắn (1 request rồi đóng) | Dài (TCP mở suốt phiên làm việc) |
| Nhận kết quả | Tính toán tại Client | Nhận adjustment từ Server |
| Tham chiếu thời gian | Server là chuẩn | Trung bình tất cả node |

### Luồng thực thi chi tiết

#### Bước 1 — Khởi tạo và hiển thị trạng thái ban đầu

```python
client = BerkeleyClient(server_ip, node_id, fake_offset)
# Đồng hồ cục bộ giả lập:
# my_clock() = time.time() + fake_offset + offset_accumulated
#                                  ↑                  ↑
#                        lệch ban đầu      tổng adj đã nhận (=0 ban đầu)
```

Console hiển thị:
```
  Server      : 192.168.1.100:5002
  Fake Offset : +5.000s
  Thời gian OS: 15:30:00.000
  Đồng hồ CL  : 15:30:05.000 (CHƯA ĐỒNG BỘ)
```

#### Bước 2 — Kết nối và đăng ký

```python
sock.connect((server_ip, 5002))
send({"type": "register", "node_id": 1, "fake_offset": 5.0})
```

Sau khi nhận `{"type": "registered"}` → Client mở vòng lặp `run()` chờ message từ Server. Kết nối TCP được **giữ mở liên tục**.

#### Bước 3 — Phản hồi POLL (handle_poll)

Khi Server gửi POLL, Client phải phản hồi **càng nhanh càng tốt** để RTT measurement của Server chính xác:

```python
def handle_poll(self, msg):
    t_client = self.my_clock()          # Đọc đồng hồ ngay lập tức
    self._send({"type": "poll_response", "client_time": t_client})
```

Tại sao lại gửi `my_clock()` chứ không phải `time.time()`?
Vì `my_clock()` là đồng hồ "Client đang sống" — đã bao gồm `fake_offset` và các điều chỉnh trước đó. Server cần biết thời gian thực sự mà Client đang dùng.

#### Bước 4 — Nhận và áp dụng ADJUST (handle_adjust)

```python
def handle_adjust(self, msg):
    adjustment = msg["adjustment"]
    t_before = self.my_clock()
    self.offset_accumulated += adjustment   # ← Áp dụng điều chỉnh
    t_after = self.my_clock()
```

**Cách mô phỏng điều chỉnh đồng hồ:**
```
my_clock() = time.time() + fake_offset + offset_accumulated

Sau khi nhận adj:
  offset_accumulated += adj
  → my_clock() dịch chuyển đúng adj giây
  → qua nhiều vòng, offset_accumulated ≈ -fake_offset
  → my_clock() ≈ time.time()  (khớp với Server)
```

Trong hệ thống thực, có 2 cách điều chỉnh:
- **Slewing**: Tăng/giảm tốc độ tick từ từ (ít gây gián đoạn, an toàn hơn)
- **Stepping**: Đặt lại đồng hồ ngay (dùng khi lệch quá lớn)

#### Bước 5 — Báo cáo Dashboard

Sau mỗi lần nhận ADJUST, Client gửi HTTP POST đến `http://<server>:8080/api/berkeley/result`:
```json
{
  "node_id": 1,
  "adjustment": -4.975,
  "avg_offset": 0.025,
  "time_before": "15:30:05.000",
  "time_after":  "15:30:00.025",
  "remaining_error_ms": 25.0,
  "fake_offset": 5.0
}
```

### Ví dụ số minh họa thuật toán Berkeley

**Tình huống:** 4 Client với fake_offset khác nhau, Server là tham chiếu.

```
Ban đầu (so với thời gian thực 15:30:00.000):
  Server  : 15:30:00.000  (offset = 0)
  Node 1  : 15:30:05.000  (offset = +5.0s, nhanh)
  Node 2  : 15:29:52.000  (offset = -8.0s, chậm)
  Node 3  : 15:30:02.000  (offset = +2.0s, nhanh)
  Node 4  : 15:29:59.000  (offset = -1.0s, chậm)

Bước 1 — Server tính offset từng node:
  offset_server = 0.0
  offset_1 = +5.0s, offset_2 = -8.0s, offset_3 = +2.0s, offset_4 = -1.0s

Bước 2 — Trung bình:
  avg = (0 + 5 - 8 + 2 - 1) / 5 = -2/5 = -0.4s

Bước 3 — Tính adj:
  adj_1 = -0.4 - (+5.0) = -5.4s  (Node 1 cần TRỪ 5.4s)
  adj_2 = -0.4 - (-8.0) = +7.6s  (Node 2 cần CỘNG 7.6s)
  adj_3 = -0.4 - (+2.0) = -2.4s  (Node 3 cần TRỪ 2.4s)
  adj_4 = -0.4 - (-1.0) = +0.6s  (Node 4 cần CỘNG 0.6s)
  (Server tự điều chỉnh: adj_server = -0.4 - 0 = -0.4s)

Sau điều chỉnh (tất cả hội tụ về -0.4s so với thực tế):
  Server  : 15:29:59.600  ← cũng điều chỉnh về trung bình
  Node 1  : 15:29:59.600  ✅ đồng bộ
  Node 2  : 15:29:59.600  ✅ đồng bộ
  Node 3  : 15:29:59.600  ✅ đồng bộ
  Node 4  : 15:29:59.600  ✅ đồng bộ
```

**Lưu ý:** Trong demo này, Server không tự điều chỉnh đồng hồ (vì `time.time()` là đồng hồ OS), nhưng theo thuật toán gốc, Server cũng phải áp dụng `adj_server = avg_offset - 0 = avg_offset`.

### Tóm tắt luồng message Berkeley

```
berkeley_client.py ──TCP──► berkeley_server.py (Port 5002)
  [Node 1]         register →
                   ← registered
                   (chờ...)
                   ← poll {"server_time": T}
                   poll_response {"client_time": my_clock()} →
                   ← adjust {"adjustment": adj, "avg_offset": avg}
                   ──HTTP POST──► dashboard.py (Port 8080) [báo kết quả]
```

---

## Tóm tắt luồng message giữa Client và Server

### NTP (Cristian)
```
ntp_client.py ──TCP──► ntp_server.py (Port 5000)
              ◄── T2, T3 ──
              ──HTTP POST──► dashboard.py (Port 8080) [báo kết quả]
```

### Berkeley
```
berkeley_client.py ──TCP──► berkeley_server.py (Port 5002)
  [Node 1]         register →
                   ← registered
                   ← poll
                   poll_response →
                   ← adjust
                   ──HTTP POST──► dashboard.py (Port 8080) [báo kết quả]
```

### Logical Clock
```
logic_client.py ──TCP──► logic_server.py (Port 5001)
  [Node 1]      register →
                ← registered
                local_event →    [server log]
                send_event →     [server forward]
                             ──► [Node 2] receive_event
                             ◄── receive_ack
```

### Định dạng message
Tất cả message giữa `berkeley_client.py` và `berkeley_server.py` là **JSON kết thúc bằng `\n`**:
```
{"type": "poll_response", "client_time": 1712644585.123}\n
```
Ký tự `\n` để bên nhận biết một message đã kết thúc và bắt đầu parse (line-buffered protocol), giống hệt logic_client/logic_server.
