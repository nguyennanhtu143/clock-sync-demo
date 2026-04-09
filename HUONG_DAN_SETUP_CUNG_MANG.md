# Hướng dẫn Setup — 5 máy cùng mạng WiFi/LAN

> Đây là cách đơn giản nhất. Tất cả 5 máy (1 Server + 4 Client) đều kết nối cùng 1 mạng WiFi hoặc cùng 1 switch mạng dây.

---

## Bước 1: Kết nối tất cả máy vào cùng 1 mạng

- Tất cả 5 máy kết nối vào **cùng 1 WiFi** (ví dụ: WiFi phòng lab, WiFi lớp học).
- Hoặc cắm dây mạng vào **cùng 1 switch/router**.
- **Lưu ý**: Một số mạng WiFi công cộng (quán cafe, trường học) có thể chặn kết nối giữa các thiết bị (AP Isolation). Nếu gặp lỗi kết nối, hãy thử cách dùng Radmin VPN trong file hướng dẫn kia.

---

## Bước 2: Lấy địa chỉ IP của máy Server

Trên **máy Server** (máy sẽ chạy `dashboard.py`), mở **Command Prompt** hoặc **PowerShell** và gõ:

```
ipconfig
```

Tìm dòng **IPv4 Address** trong phần **Wireless LAN adapter Wi-Fi** (nếu dùng WiFi) hoặc **Ethernet adapter** (nếu dùng dây):

```
Wireless LAN adapter Wi-Fi:

   Connection-specific DNS Suffix  . :
   IPv4 Address. . . . . . . . . . . : 192.168.1.100    ← ĐÂY LÀ IP SERVER
   Subnet Mask . . . . . . . . . . . : 255.255.255.0
   Default Gateway . . . . . . . . . : 192.168.1.1
```

**Ghi nhớ IP này** (ví dụ: `192.168.1.100`). Thông báo cho 4 máy Client.

---

## Bước 3: Kiểm tra kết nối (tùy chọn nhưng khuyến khích)

Trên **mỗi máy Client**, mở CMD và ping đến IP Server:

```
ping 192.168.1.100
```

Nếu thấy phản hồi (`Reply from 192.168.1.100...`) → ✅ kết nối OK.
Nếu thấy `Request timed out` → ❌ kiểm tra lại mạng hoặc tắt Firewall.

### Tắt Windows Firewall (nếu bị chặn):

Trên **máy Server**, mở CMD **với quyền Admin** và chạy:

```
netsh advfirewall set allprofiles state off
```

> ⚠️ Nhớ bật lại sau khi demo xong:
> ```
> netsh advfirewall set allprofiles state on
> ```

Hoặc chỉ mở 3 port cần thiết (an toàn hơn):

```
netsh advfirewall firewall add rule name="NTP Server" dir=in action=allow protocol=TCP localport=5000
netsh advfirewall firewall add rule name="Logic Server" dir=in action=allow protocol=TCP localport=5001
netsh advfirewall firewall add rule name="Dashboard" dir=in action=allow protocol=TCP localport=8080
```

---

## Bước 4: Chạy Server

Trên **máy Server**, mở PowerShell/CMD:

```bash
cd d:\HTPT\server
venv\Scripts\activate
python dashboard.py
```

Sẽ thấy thông báo:
```
═══════════════════════════════════════════════════════
║       DISTRIBUTED TIME SYNC — DASHBOARD            ║
═══════════════════════════════════════════════════════
║  NTP Server ............. Port 5000                 ║
║  Logic Server ........... Port 5001                 ║
║  Web Dashboard .......... Port 8080                 ║
═══════════════════════════════════════════════════════
```

Mở browser trên máy Server: `http://localhost:8080` để xem Dashboard.
Các máy Client cũng có thể mở: `http://192.168.1.100:8080`

---

## Bước 5: Chạy NTP Client (trên 4 máy Client)

Trên **mỗi máy Client**, mở PowerShell/CMD:

```bash
cd d:\HTPT\client
venv\Scripts\activate

# Thay 192.168.1.100 bằng IP thực của Server
# Thay --node-id bằng số khác nhau cho mỗi máy (1, 2, 3, 4)
python ntp_client.py --server-ip 192.168.1.100 --node-id 1
```

**Phân chia node-id:**
| Máy       | Lệnh                                                              |
|-----------|--------------------------------------------------------------------|
| Client 1  | `python ntp_client.py --server-ip 192.168.1.100 --node-id 1`     |
| Client 2  | `python ntp_client.py --server-ip 192.168.1.100 --node-id 2`     |
| Client 3  | `python ntp_client.py --server-ip 192.168.1.100 --node-id 3`     |
| Client 4  | `python ntp_client.py --server-ip 192.168.1.100 --node-id 4`     |

Khi thấy `Nhấn Enter để bắt đầu đồng bộ NTP...` → người điều phối hô "bắt đầu" → tất cả nhấn Enter.

---

## Bước 6: Chạy Logical Clock Client (trên 4 máy Client)

Sau khi demo NTP xong, chạy Logical Clock:

```bash
python logic_client.py --server-ip 192.168.1.100 --node-id 1
```

Sử dụng menu tương tác để tạo sự kiện:
1. **Local Event** — Sự kiện nội bộ
2. **Send Message** — Gửi message đến node khác
3. **Xem Clock** — Xem trạng thái Lamport & Vector Clock

---

## Bước 7: Xem kết quả trên Dashboard

Mở browser: `http://192.168.1.100:8080`
- **Tab NTP Sync**: Biểu đồ offset, delay, bảng kết quả chi tiết
- **Tab Logical Clocks**: Space-time diagram, bảng sự kiện
- **Tab So sánh**: So sánh Lamport vs Vector vs NTP

---

## Tóm tắt

```
5 máy cùng WiFi/LAN
       ↓
Lấy IP Server (ipconfig)
       ↓
Ping kiểm tra + mở Firewall nếu cần
       ↓
Server: python dashboard.py
       ↓
4 Client: python ntp_client.py --server-ip <IP> --node-id <1-4>
       ↓
4 Client: python logic_client.py --server-ip <IP> --node-id <1-4>
       ↓
Xem Dashboard: http://<IP>:8080
```
