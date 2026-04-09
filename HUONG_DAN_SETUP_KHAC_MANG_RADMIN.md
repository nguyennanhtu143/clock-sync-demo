# Hướng dẫn Setup — 5 máy KHÁC mạng, dùng Radmin VPN

> Sử dụng khi 5 máy (1 Server + 4 Client) đang ở **khác mạng WiFi** (ví dụ: mỗi người ở nhà riêng, hoặc mạng trường chặn kết nối giữa các thiết bị).
> Radmin VPN sẽ tạo một **mạng LAN ảo** để các máy "nhìn thấy" nhau như đang cùng mạng.

---

## Radmin VPN là gì?

- Phần mềm **miễn phí** tạo mạng LAN ảo (Virtual LAN) qua Internet.
- Mỗi máy sẽ được cấp 1 IP ảo (dạng `26.x.x.x`).
- Các máy trong cùng 1 "Network" trên Radmin VPN sẽ kết nối được với nhau, dù ở bất kỳ đâu.

---

## Bước 1: Cài đặt Radmin VPN trên TẤT CẢ 5 máy

### 1.1. Tải Radmin VPN

- Truy cập: **https://www.radmin-vpn.com/**
- Nhấn **"Download for free"** → tải file `RadminVPN.exe`
- Chạy file cài đặt → nhấn **Next** → **Install** → **Finish**

### 1.2. Khởi động Radmin VPN

- Mở **Radmin VPN** từ Desktop hoặc Start Menu
- Giao diện sẽ hiện ra với 1 IP ảo (ví dụ: `26.55.xxx.xxx`)

---

## Bước 2: Tạo mạng chung trên Radmin VPN

### Trên máy Server (người tạo mạng):

1. Mở Radmin VPN
2. Nhấn **"Create Network"** (hoặc "Tạo mạng")
3. Điền thông tin:
   - **Network Name**: `HTPT_Demo` (hoặc tên bất kỳ)
   - **Password**: `123456` (hoặc mật khẩu bất kỳ, chia sẻ cho 4 Client)
4. Nhấn **"Create"**

### Trên 4 máy Client (người tham gia):

1. Mở Radmin VPN
2. Nhấn **"Join Network"** (hoặc "Tham gia mạng")
3. Điền thông tin:
   - **Network Name**: `HTPT_Demo` (phải giống hệt Server đã tạo)
   - **Password**: `123456` (phải giống hệt)
4. Nhấn **"Join"**

### Kết quả:

Sau khi tất cả 5 máy join vào cùng network, Radmin VPN sẽ hiển thị danh sách 5 máy với IP ảo:

```
┌─────────────────────────────────────────────┐
│  Network: HTPT_Demo                         │
├─────────────────────────────────────────────┤
│  ● My PC (Server)     26.55.10.1     Online │
│  ● Client-1           26.55.10.2     Online │
│  ● Client-2           26.55.10.3     Online │
│  ● Client-3           26.55.10.4     Online │
│  ● Client-4           26.55.10.5     Online │
└─────────────────────────────────────────────┘
```

> **Lưu ý**: IP thực tế sẽ khác, tùy Radmin cấp. Ghi nhớ IP của máy Server.

---

## Bước 3: Lấy IP Radmin của máy Server

Trên **máy Server**, xem IP trong giao diện Radmin VPN (hiển thị ngay trên cùng).

**Hoặc** mở CMD và gõ:

```
ipconfig
```

Tìm phần **Ethernet adapter Radmin VPN**:

```
Ethernet adapter Radmin VPN:

   IPv4 Address. . . . . . . . . . . : 26.55.10.1    ← ĐÂY LÀ IP RADMIN CỦA SERVER
   Subnet Mask . . . . . . . . . . . : 255.0.0.0
```

**Thông báo IP này cho 4 Client** (ví dụ: `26.55.10.1`).

---

## Bước 4: Kiểm tra kết nối qua Radmin VPN

Trên **mỗi máy Client**, ping đến IP Radmin của Server:

```
ping 26.55.10.1
```

✅ Nếu thấy `Reply from 26.55.10.1...` → Kết nối OK.
❌ Nếu thấy `Request timed out`:
- Kiểm tra cả 2 máy đã join cùng network trên Radmin VPN chưa
- Kiểm tra Radmin VPN đang hiển thị **Online** (chấm xanh)
- Thử tắt Windows Firewall trên máy Server (xem hướng dẫn bên dưới)

### Tắt Firewall (nếu cần):

Trên **máy Server**, mở CMD **với quyền Admin**:

```
netsh advfirewall set allprofiles state off
```

> ⚠️ Nhớ bật lại sau demo:
> ```
> netsh advfirewall set allprofiles state on
> ```

Hoặc chỉ mở 3 port (an toàn hơn):

```
netsh advfirewall firewall add rule name="NTP Server" dir=in action=allow protocol=TCP localport=5000
netsh advfirewall firewall add rule name="Logic Server" dir=in action=allow protocol=TCP localport=5001
netsh advfirewall firewall add rule name="Dashboard" dir=in action=allow protocol=TCP localport=8080
```

---

## Bước 5: Chạy Server

Trên **máy Server**, mở PowerShell/CMD:

```bash
cd d:\HTPT\server

# Nếu lỡ copy thư mục venv từ máy khác sang thì xóa đi: rmdir /s /q venv

# Tạo venv MỚI trên máy này (chỉ cần làm 1 lần)
python -m venv venv

# Kích hoạt
venv\Scripts\activate

# Cài đặt
pip install -r requirements.txt

# Chạy server
python dashboard.py
```

Sẽ thấy:
```
═══════════════════════════════════════════════════════
║       DISTRIBUTED TIME SYNC — DASHBOARD            ║
═══════════════════════════════════════════════════════
║  NTP Server ............. Port 5000                 ║
║  Logic Server ........... Port 5001                 ║
║  Web Dashboard .......... Port 8080                 ║
═══════════════════════════════════════════════════════
```

Mở browser:
- Trên Server: `http://localhost:8080`
- Trên Client: `http://26.55.10.1:8080` (thay bằng IP Radmin thực của Server)

---

## Bước 6: Chạy NTP Client (trên 4 máy Client)

Trên **mỗi máy Client**:

```bash
cd d:\HTPT\client

# Tạo venv MỚI trên máy này (chỉ cần làm 1 lần)
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# ⚠️ DÙNG IP RADMIN CỦA SERVER (không phải IP WiFi)
python ntp_client.py --server-ip 26.55.10.1 --node-id 1
```

**Phân chia node-id:**
| Máy       | Lệnh                                                           |
|-----------|-----------------------------------------------------------------|
| Client 1  | `python ntp_client.py --server-ip 26.55.10.1 --node-id 1`     |
| Client 2  | `python ntp_client.py --server-ip 26.55.10.1 --node-id 2`     |
| Client 3  | `python ntp_client.py --server-ip 26.55.10.1 --node-id 3`     |
| Client 4  | `python ntp_client.py --server-ip 26.55.10.1 --node-id 4`     |

> ⚠️ **Quan trọng**: Luôn dùng **IP Radmin** (`26.x.x.x`), KHÔNG dùng IP WiFi (`192.168.x.x`).

Khi thấy `Nhấn Enter để bắt đầu đồng bộ NTP...` → người điều phối hô "bắt đầu" → tất cả nhấn Enter.

---

## Bước 7: Chạy Logical Clock Client (trên 4 máy Client)

```bash
python logic_client.py --server-ip 26.55.10.1 --node-id 1
```

---

## Bước 8: Xem Dashboard

Mở browser trên **bất kỳ máy nào**: `http://26.55.10.1:8080`

---

## Lưu ý quan trọng khi dùng Radmin VPN

### ⚠️ Độ trễ mạng sẽ cao hơn

- Khi dùng Radmin VPN, dữ liệu đi qua **Internet**, nên delay sẽ lớn hơn nhiều so với cùng LAN (có thể 20-100ms thay vì 1-5ms).
- Điều này **KHÔNG ảnh hưởng** đến kết quả demo, vì NTP sẽ tính đúng delay và bù offset.
- Thực tế, delay lớn hơn sẽ cho demo **trực quan hơn**!

### ⚠️ Đảm bảo Radmin VPN luôn chạy

- Radmin VPN phải **mở liên tục** trong suốt quá trình demo.
- Nếu mất kết nối, chỉ cần mở lại Radmin VPN → tự động reconnect.

### ⚠️ Sau khi demo xong

1. Bật lại Firewall (nếu đã tắt):
   ```
   netsh advfirewall set allprofiles state on
   ```
2. Có thể rời khỏi network Radmin VPN:
   - Mở Radmin VPN → chuột phải vào network → **Leave Network**
3. Hoặc gỡ cài đặt Radmin VPN nếu không cần nữa.

---

## Xử lý sự cố

| Lỗi | Nguyên nhân | Cách sửa |
|------|------------|----------|
| `ping` không phản hồi | Firewall chặn | Tắt Firewall hoặc mở port |
| `Connection refused` | Server chưa chạy | Chạy `python dashboard.py` trên Server trước |
| `Connection timed out` | IP sai hoặc Radmin chưa kết nối | Kiểm tra IP Radmin, đảm bảo Online |
| Radmin hiện "Offline" | Mạng Internet bị mất | Kiểm tra Internet trên máy đó |
| `Network not found` khi Join | Tên mạng sai | Kiểm tra lại tên mạng (phân biệt hoa thường) |

---

## Tóm tắt

```
Cài Radmin VPN trên 5 máy
            ↓
Server tạo Network (ví dụ: HTPT_Demo / 123456)
            ↓
4 Client join cùng Network
            ↓
Lấy IP Radmin của Server (26.x.x.x)
            ↓
Ping kiểm tra + mở Firewall nếu cần
            ↓
Server:  python dashboard.py
            ↓
Client:  python ntp_client.py --server-ip 26.x.x.x --node-id <1-4>
            ↓
Client:  python logic_client.py --server-ip 26.x.x.x --node-id <1-4>
            ↓
Dashboard: http://26.x.x.x:8080
```
