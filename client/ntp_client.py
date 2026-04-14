"""
NTP Client - Gửi yêu cầu đồng bộ thời gian đến NTP Server
Chạy trên các máy Client (Node 1-4).
Fake offset để demo hiệu quả đồng bộ.
"""

import socket
import json
import time
import argparse
import random
from datetime import datetime

SERVER_PORT = 5000
DASHBOARD_PORT = 8080


def get_timestamp():
    """Trả về timestamp hiện tại (float seconds)"""
    return time.time()


def format_time(ts):
    """Format timestamp thành chuỗi dễ đọc"""
    return datetime.fromtimestamp(ts).strftime("%H:%M:%S.%f")[:-3]


def log(level, msg):
    ts = format_time(time.time())
    print(f"[{ts}] [{level}] {msg}")


def perform_ntp_sync(server_ip, node_id, fake_offset):
    """Thực hiện NTP synchronization"""
    os_time = get_timestamp()
    client_time = os_time + fake_offset

    print(f"\n--- NTP CLIENT Node {node_id} ---")
    print(f"  Server      : {server_ip}:{SERVER_PORT}")
    print(f"  Thời gian OS: {format_time(os_time)}")
    print(f"  Fake Offset : {fake_offset:+.3f}s")
    print(f"  Client Time : {format_time(client_time)} (CHUA DONG BO)")

    input("\nNhan Enter de bat dau dong bo NTP...\n")

    log("INFO", "Bắt đầu quá trình đồng bộ NTP...")

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect((server_ip, SERVER_PORT))

        # T1: Thời gian Client gửi request
        t1 = get_timestamp() + fake_offset
        log("SEND", f"NTP Request -> Server | T1={format_time(t1)}")

        request = json.dumps({"node_id": node_id, "T1": t1})
        sock.sendall(request.encode("utf-8"))

        data = sock.recv(4096).decode("utf-8")

        # T4: Thời gian Client nhận response
        real_recv_time = time.time()       # thời gian OS thực (không có fake offset)
        t4 = real_recv_time + fake_offset  # thời gian "Client thấy"

        response = json.loads(data)
        t2 = response["T2"]
        t3 = response["T3"]

        log("RECV", f"NTP Response <- Server | T2={format_time(t2)} T3={format_time(t3)} T4={format_time(t4)}")
        sock.close()

    except Exception as e:
        log("ERROR", f"Lỗi kết nối: {e}")
        return

    # Tính toán Delay và Offset
    delay = ((t2 - t1) + (t4 - t3)) / 2
    offset = ((t2 - t1) - (t4 - t3)) / 2

    corrected_time = time.time() + fake_offset + offset
    # Ước tính thời gian server hiện tại từ T3 (dùng đồng hồ server, không dùng đồng hồ client bị lệch)
    time_elapsed_since_recv = time.time() - real_recv_time
    estimated_server_now = t3 + time_elapsed_since_recv

    print(f"\n--- KET QUA DONG BO NTP Node {node_id} ---")
    print(f"  T1 (Client gui) : {format_time(t1)}")
    print(f"  T2 (Server nhan): {format_time(t2)}")
    print(f"  T3 (Server gui) : {format_time(t3)}")
    print(f"  T4 (Client nhan): {format_time(t4)}")
    print(f"  Delay (d)       : {delay * 1000:.3f}ms")
    print(f"  Offset (θ)      : {offset:+.6f}s")
    print(f"  Truoc dong bo   : {format_time(t4)}")
    print(f"  Sau dong bo     : {format_time(corrected_time)}")
    print(f"  Server Time (uo tinh): {format_time(estimated_server_now)}")
    print(f"  Sai lech con lai: {abs(corrected_time - estimated_server_now) * 1000:.3f}ms")
    print(f"  Trang thai      : DA DONG BO\n")

    # Report cho Dashboard
    total_offset = fake_offset + offset
    report_to_dashboard(server_ip, {
        "node_id": node_id,
        "T1": t1, "T2": t2, "T3": t3, "T4": t4,
        "delay": delay,
        "offset": offset,
        "fake_offset": fake_offset,
        "total_offset": total_offset,
        "before_sync": format_time(t4),
        "after_sync": format_time(corrected_time),
        "server_time": format_time(estimated_server_now),
        "remaining_error_ms": abs(corrected_time - estimated_server_now) * 1000,
    })

    # Hiển thị thời gian đã hiệu chỉnh
    print(f"Hien thi thoi gian da hieu chinh (Ctrl+C de dung):\n")
    try:
        for i in range(30):
            now = get_timestamp()
            raw_str = format_time(now + fake_offset)
            synced_str = format_time(now + fake_offset + offset)
            server_str = format_time(now)
            print(f"  [{i + 1:>2}/30]  Server: {server_str}  |  Raw: {raw_str}  |  Synced: {synced_str}")
            time.sleep(1)
    except KeyboardInterrupt:
        pass

    print(f"\nDemo NTP hoan tat cho Node {node_id}.\n")


def report_to_dashboard(server_ip, data):
    """Gửi kết quả NTP về Dashboard server"""
    try:
        import requests
        url = f"http://{server_ip}:{DASHBOARD_PORT}/api/ntp/result"
        requests.post(url, json=data, timeout=3)
        log("INFO", f"Đã gửi kết quả về Dashboard ({server_ip}:{DASHBOARD_PORT})")
    except Exception:
        log("WARN", "Không thể gửi kết quả về Dashboard (Dashboard có thể chưa chạy)")


def main():
    parser = argparse.ArgumentParser(description="NTP Client - Đồng bộ thời gian")
    parser.add_argument("--server-ip", required=True, help="Địa chỉ IP của NTP Server")
    parser.add_argument("--node-id", type=int, required=True, choices=[1, 2, 3, 4],
                        help="ID của node client (1-4)")
    parser.add_argument("--fake-offset", type=float, default=None,
                        help="Fake offset (giây). Mặc định: random [-10, +10]")
    args = parser.parse_args()

    if args.fake_offset is None:
        args.fake_offset = round(random.uniform(-10, 10), 3)

    print(f"\n=== HE THONG DONG BO THOI GIAN PHAN TAN | NTP Client Node {args.node_id} ===\n")

    perform_ntp_sync(args.server_ip, args.node_id, args.fake_offset)


if __name__ == "__main__":
    main()
