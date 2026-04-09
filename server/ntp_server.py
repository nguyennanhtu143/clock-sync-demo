"""
NTP Time Server - Đồng bộ đồng hồ vật lý (Physical Clock Synchronization)
Chạy trên máy Server (Node 0), lắng nghe yêu cầu đồng bộ từ các Client.
Port: 5000 (TCP)
"""

import socket
import threading
import json
import time
import sys
from datetime import datetime

from colorama import init, Fore, Style, Back

init(autoreset=True)

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


def log(level, msg, color=Fore.WHITE):
    """In log có màu với timestamp"""
    ts = format_time(time.time())
    prefix_map = {
        "INFO": f"{Fore.CYAN}[{ts}] {Fore.GREEN}[NTP]{Style.RESET_ALL}",
        "RECV": f"{Fore.CYAN}[{ts}] {Fore.YELLOW}[NTP ←]{Style.RESET_ALL}",
        "SEND": f"{Fore.CYAN}[{ts}] {Fore.BLUE}[NTP →]{Style.RESET_ALL}",
        "ERROR": f"{Fore.CYAN}[{ts}] {Fore.RED}[NTP ✗]{Style.RESET_ALL}",
        "SUCCESS": f"{Fore.CYAN}[{ts}] {Fore.GREEN}[NTP ✓]{Style.RESET_ALL}",
    }
    prefix = prefix_map.get(level, f"[{ts}] [{level}]")
    print(f"  {prefix} {color}{msg}{Style.RESET_ALL}")


def print_banner():
    """In banner khởi động server"""
    banner = f"""
{Fore.CYAN}{'═' * 60}
{Fore.CYAN}║{Fore.WHITE}{Back.BLUE}{'NTP TIME SERVER':^58}{Style.RESET_ALL}{Fore.CYAN}║
{Fore.CYAN}{'═' * 60}
{Fore.CYAN}║{Style.RESET_ALL}  {'Role:':<15} {Fore.YELLOW}Master Clock (Node 0){Style.RESET_ALL}{'':>17}{Fore.CYAN}║
{Fore.CYAN}║{Style.RESET_ALL}  {'Protocol:':<15} {Fore.YELLOW}TCP{Style.RESET_ALL}{'':>34}{Fore.CYAN}║
{Fore.CYAN}║{Style.RESET_ALL}  {'Port:':<15} {Fore.YELLOW}{PORT}{Style.RESET_ALL}{'':>33}{Fore.CYAN}║
{Fore.CYAN}║{Style.RESET_ALL}  {'Process Delay:':<15} {Fore.YELLOW}{int(PROCESSING_DELAY * 1000)}ms{Style.RESET_ALL}{'':>31}{Fore.CYAN}║
{Fore.CYAN}║{Style.RESET_ALL}  {'Server Time:':<15} {Fore.GREEN}{format_time(time.time())}{Style.RESET_ALL}{'':>24}{Fore.CYAN}║
{Fore.CYAN}{'═' * 60}{Style.RESET_ALL}
"""
    print(banner)


def handle_client(conn, addr):
    """Xử lý một kết nối NTP từ client"""
    try:
        # Nhận dữ liệu từ client
        data = conn.recv(4096).decode("utf-8")
        if not data:
            return

        request = json.loads(data)
        node_id = request.get("node_id", "?")
        t1 = request.get("T1", 0)

        # ===== T2: Thời gian Server nhận =====
        t2 = get_timestamp()
        log("RECV", f"Request từ {Fore.YELLOW}Client {node_id}{Style.RESET_ALL} ({addr[0]}:{addr[1]})")
        log("INFO", f"  T1 (Client gửi) = {Fore.WHITE}{format_time(t1)}{Style.RESET_ALL}")
        log("INFO", f"  T2 (Server nhận) = {Fore.WHITE}{format_time(t2)}{Style.RESET_ALL}")

        # Mô phỏng processing delay
        time.sleep(PROCESSING_DELAY)

        # ===== T3: Thời gian Server gửi =====
        t3 = get_timestamp()
        log("INFO", f"  T3 (Server gửi)  = {Fore.WHITE}{format_time(t3)}{Style.RESET_ALL}")

        # Gửi response về client
        response = json.dumps({
            "T2": t2,
            "T3": t3,
            "server_time": get_timestamp()
        })
        conn.sendall(response.encode("utf-8"))

        log("SEND", f"Response → {Fore.YELLOW}Client {node_id}{Style.RESET_ALL} | T2={format_time(t2)} T3={format_time(t3)}")
        log("SUCCESS", f"Hoàn thành đồng bộ cho Client {node_id}")
        print(f"  {Fore.CYAN}{'─' * 58}{Style.RESET_ALL}")

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
    print_banner()

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen(5)

    log("INFO", f"Server đang lắng nghe trên {Fore.GREEN}{HOST}:{PORT}{Style.RESET_ALL}")
    log("INFO", f"Thời gian Master Clock: {Fore.GREEN}{format_time(time.time())}{Style.RESET_ALL}")
    log("INFO", "Đang chờ kết nối từ các Client...")
    print(f"  {Fore.CYAN}{'─' * 58}{Style.RESET_ALL}")

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
