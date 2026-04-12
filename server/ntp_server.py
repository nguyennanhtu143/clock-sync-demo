"""
NTP Time Server - Đồng bộ đồng hồ vật lý (Physical Clock Synchronization)
Chạy trên máy Server (Node 0), lắng nghe yêu cầu đồng bộ từ các Client.
Port: 5000 (TCP)
"""

import socket
import threading
import json
import time
from datetime import datetime

HOST = "0.0.0.0"
PORT = 5000
PROCESSING_DELAY = 0.05  # 50ms mô phỏng processing delay

# Shared state cho dashboard
ntp_results = {}
ntp_lock = threading.Lock()


def get_timestamp():
    """Trả về timestamp hiện tại (float seconds)"""
    return time.time()


def format_time(ts):
    """Format timestamp thành chuỗi dễ đọc"""
    return datetime.fromtimestamp(ts).strftime("%H:%M:%S.%f")[:-3]


def log(level, msg):
    """In log với timestamp"""
    ts = format_time(time.time())
    print(f"[{ts}] [{level}] {msg}")


def handle_client(conn, addr):
    """Xử lý một kết nối NTP từ client"""
    try:
        data = conn.recv(4096).decode("utf-8")
        if not data:
            return

        request = json.loads(data)
        node_id = request.get("node_id", "?")
        t1 = request.get("T1", 0)

        # T2: Thời gian Server nhận
        t2 = get_timestamp()

        # Mô phỏng processing delay
        time.sleep(PROCESSING_DELAY)

        # T3: Thời gian Server gửi
        t3 = get_timestamp()

        response = json.dumps({
            "T2": t2,
            "T3": t3,
            "server_time": get_timestamp()
        })
        conn.sendall(response.encode("utf-8"))

        log("NTP", f"Client {node_id} ({addr[0]}) | T2={format_time(t2)} T3={format_time(t3)}")

        # Lưu vào shared state cho dashboard
        with ntp_lock:
            ntp_results[str(node_id)] = {
                "node_id": node_id,
                "ip": addr[0],
                "T1": t1,
                "T2": t2,
                "T3": t3,
                "timestamp": time.time()
            }

    except Exception as e:
        log("ERROR", f"Lỗi xử lý client {addr}: {e}")
    finally:
        conn.close()


def get_ntp_results():
    """Trả về kết quả NTP cho dashboard"""
    with ntp_lock:
        return dict(ntp_results)


def start_server():
    """Khởi động NTP Server"""
    print(f"=== NTP TIME SERVER | Port {PORT} | Processing delay {int(PROCESSING_DELAY * 1000)}ms ===")

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen(5)

    log("INFO", f"Đang lắng nghe trên {HOST}:{PORT}")

    try:
        while True:
            conn, addr = server_socket.accept()
            thread = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            thread.start()
    except KeyboardInterrupt:
        log("INFO", "Server đang tắt...")
    finally:
        server_socket.close()


if __name__ == "__main__":
    start_server()
