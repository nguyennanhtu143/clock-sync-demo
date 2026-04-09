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
import sys
from datetime import datetime

from colorama import init, Fore, Style, Back

init(autoreset=True)

SERVER_PORT = 5000
DASHBOARD_PORT = 8080


def get_timestamp():
    """Trả về timestamp hiện tại (float seconds)"""
    return time.time()


def format_time(ts):
    """Format timestamp thành chuỗi dễ đọc"""
    return datetime.fromtimestamp(ts).strftime("%H:%M:%S.%f")[:-3]


def format_time_full(ts):
    """Format timestamp đầy đủ"""
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


# ═══════════════════════════════════════════════
# Console UI helpers
# ═══════════════════════════════════════════════

NODE_COLORS = {
    1: Fore.GREEN,
    2: Fore.YELLOW,
    3: Fore.MAGENTA,
    4: Fore.CYAN,
}


def get_color(node_id):
    return NODE_COLORS.get(node_id, Fore.WHITE)


def print_box(lines, title="", color=Fore.CYAN, width=56):
    """In hộp với border có tiêu đề"""
    print()
    # Top border
    if title:
        padding = width - len(title) - 4
        left_pad = padding // 2
        right_pad = padding - left_pad
        print(f"  {color}╔{'═' * left_pad} {Style.BRIGHT}{title} {Style.RESET_ALL}{color}{'═' * right_pad}╗{Style.RESET_ALL}")
    else:
        print(f"  {color}╔{'═' * width}╗{Style.RESET_ALL}")

    # Content
    for line in lines:
        # Tính padding nếu line không có ANSI codes
        visible_len = len(line.encode('ascii', errors='ignore').decode())
        # Simplified: just pad to width
        print(f"  {color}║{Style.RESET_ALL} {line:<{width - 2}} {color}║{Style.RESET_ALL}")

    # Bottom border
    print(f"  {color}╚{'═' * width}╝{Style.RESET_ALL}")
    print()


def print_separator(color=Fore.CYAN, width=58):
    print(f"  {color}{'─' * width}{Style.RESET_ALL}")


def log(level, msg, color=Fore.WHITE):
    ts = format_time(time.time())
    icons = {
        "INFO": f"{Fore.GREEN}ℹ{Style.RESET_ALL}",
        "SEND": f"{Fore.BLUE}↑{Style.RESET_ALL}",
        "RECV": f"{Fore.YELLOW}↓{Style.RESET_ALL}",
        "CALC": f"{Fore.MAGENTA}⚙{Style.RESET_ALL}",
        "OK": f"{Fore.GREEN}✓{Style.RESET_ALL}",
        "WARN": f"{Fore.YELLOW}⚠{Style.RESET_ALL}",
        "TIME": f"{Fore.CYAN}⏱{Style.RESET_ALL}",
    }
    icon = icons.get(level, " ")
    print(f"  {Fore.CYAN}[{ts}]{Style.RESET_ALL} {icon} {color}{msg}{Style.RESET_ALL}")


# ═══════════════════════════════════════════════
# NTP Logic
# ═══════════════════════════════════════════════

def perform_ntp_sync(server_ip, node_id, fake_offset):
    """Thực hiện NTP synchronization"""
    node_color = get_color(node_id)

    # ── Bước 1: Hiển thị trạng thái trước đồng bộ ──
    os_time = get_timestamp()
    client_time = os_time + fake_offset

    print_box([
        f"{'Node ID:':<20} {node_color}Node {node_id}{Style.RESET_ALL}",
        f"{'Server:':<20} {server_ip}:{SERVER_PORT}",
        f"{'Thời gian OS:':<20} {Fore.WHITE}{format_time(os_time)}{Style.RESET_ALL}",
        f"{'Fake Offset:':<20} {Fore.RED}{fake_offset:+.3f}s{Style.RESET_ALL}",
        f"{'Thời gian Client:':<20} {Fore.YELLOW}{format_time(client_time)}{Style.RESET_ALL}",
        f"{'Trạng thái:':<20} {Fore.RED}❌ CHƯA ĐỒNG BỘ{Style.RESET_ALL}",
    ], title=f"NTP CLIENT — NODE {node_id}", color=node_color)

    # ── Bước 2: Chờ lệnh bắt đầu ──
    print(f"  {Fore.YELLOW}⏳ Nhấn Enter để bắt đầu đồng bộ NTP...{Style.RESET_ALL}")
    input()

    log("INFO", "Bắt đầu quá trình đồng bộ NTP...")
    print_separator()

    # ── Bước 3: NTP Exchange ──
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect((server_ip, SERVER_PORT))

        # T1: Thời gian Client gửi request (mô phỏng với fake offset)
        t1 = get_timestamp() + fake_offset
        log("SEND", f"Gửi NTP Request → Server | T1 = {format_time(t1)}")

        # Gửi request
        request = json.dumps({
            "node_id": node_id,
            "T1": t1
        })
        sock.sendall(request.encode("utf-8"))

        # Nhận response
        data = sock.recv(4096).decode("utf-8")
        
        # T4: Thời gian Client nhận response (mô phỏng với fake offset)
        t4 = get_timestamp() + fake_offset

        response = json.loads(data)
        t2 = response["T2"]
        t3 = response["T3"]

        log("RECV", f"Nhận NTP Response ← Server | T2 = {format_time(t2)}, T3 = {format_time(t3)}")
        log("INFO", f"T4 (Client nhận) = {format_time(t4)}")

        sock.close()

    except Exception as e:
        log("WARN", f"Lỗi kết nối: {e}")
        return

    # ── Bước 4: Tính toán ──
    print_separator()
    log("CALC", "Đang tính toán Delay và Offset...")

    delay = ((t2 - t1) + (t4 - t3)) / 2
    offset = ((t2 - t1) - (t4 - t3)) / 2

    log("CALC", f"Delay (δ) = ((T2-T1) + (T4-T3)) / 2 = {delay * 1000:.1f}ms")
    log("CALC", f"Offset (θ) = ((T2-T1) - (T4-T3)) / 2 = {offset:+.6f}s")

    # Thời gian sau hiệu chỉnh
    corrected_time = get_timestamp() + fake_offset + offset
    server_time_now = get_timestamp()

    # ── Bước 5: Hiển thị kết quả ──
    print_box([
        f"{'T1 (Client gửi):':<24} {Fore.WHITE}{format_time(t1)}{Style.RESET_ALL}",
        f"{'T2 (Server nhận):':<24} {Fore.WHITE}{format_time(t2)}{Style.RESET_ALL}",
        f"{'T3 (Server gửi):':<24} {Fore.WHITE}{format_time(t3)}{Style.RESET_ALL}",
        f"{'T4 (Client nhận):':<24} {Fore.WHITE}{format_time(t4)}{Style.RESET_ALL}",
        f"{'─' * 54}",
        f"{'Delay (δ):':<24} {Fore.YELLOW}{delay * 1000:.3f}ms{Style.RESET_ALL}",
        f"{'Offset (θ):':<24} {Fore.YELLOW}{offset:+.6f}s{Style.RESET_ALL}",
        f"{'─' * 54}",
        f"{'TRƯỚC đồng bộ:':<24} {Fore.RED}{format_time(t4)}{Style.RESET_ALL}",
        f"{'SAU đồng bộ:':<24} {Fore.GREEN}{format_time(corrected_time)}{Style.RESET_ALL}",
        f"{'Server Time (ref):':<24} {Fore.CYAN}{format_time(server_time_now)}{Style.RESET_ALL}",
        f"{'Sai lệch còn lại:':<24} {Fore.GREEN}{abs(corrected_time - server_time_now) * 1000:.3f}ms{Style.RESET_ALL}",
        f"{'Trạng thái:':<24} {Fore.GREEN}✅ ĐÃ ĐỒNG BỘ{Style.RESET_ALL}",
    ], title="KẾT QUẢ ĐỒNG BỘ NTP", color=Fore.GREEN)

    # ── Bước 6: Report cho Dashboard ──
    total_offset = fake_offset + offset
    report_to_dashboard(server_ip, {
        "node_id": node_id,
        "T1": t1,
        "T2": t2,
        "T3": t3,
        "T4": t4,
        "delay": delay,
        "offset": offset,
        "fake_offset": fake_offset,
        "total_offset": total_offset,
        "before_sync": format_time(t4),
        "after_sync": format_time(corrected_time),
        "server_time": format_time(server_time_now),
        "remaining_error_ms": abs(corrected_time - server_time_now) * 1000,
    })

    # ── Bước 7: Xác minh liên tục ──
    print(f"\n  {Fore.GREEN}⏱  Hiển thị thời gian đã hiệu chỉnh (Ctrl+C để dừng):{Style.RESET_ALL}\n")
    try:
        for i in range(30):
            now = get_timestamp()
            raw_time = now + fake_offset
            synced_time = now + fake_offset + offset

            raw_str = format_time(raw_time)
            synced_str = format_time(synced_time)
            server_str = format_time(now)

            bar = f"  {Fore.CYAN}[{i + 1:>2}/30]{Style.RESET_ALL}"
            print(f"{bar}  Server: {Fore.CYAN}{server_str}{Style.RESET_ALL}"
                  f"  |  Raw: {Fore.RED}{raw_str}{Style.RESET_ALL}"
                  f"  |  Synced: {Fore.GREEN}{synced_str}{Style.RESET_ALL}", end="\r\n")
            time.sleep(1)
    except KeyboardInterrupt:
        pass

    print(f"\n  {Fore.GREEN}✓ Demo NTP hoàn tất cho Node {node_id}.{Style.RESET_ALL}\n")


def report_to_dashboard(server_ip, data):
    """Gửi kết quả NTP về Dashboard server"""
    try:
        import requests
        url = f"http://{server_ip}:{DASHBOARD_PORT}/api/ntp/result"
        requests.post(url, json=data, timeout=3)
        log("OK", f"Đã gửi kết quả về Dashboard ({server_ip}:{DASHBOARD_PORT})")
    except Exception:
        log("WARN", "Không thể gửi kết quả về Dashboard (Dashboard có thể chưa chạy)")


# ═══════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════

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

    print(f"\n{Fore.CYAN}{'═' * 60}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}║{Style.RESET_ALL}{' ' * 10}{Fore.WHITE}{Style.BRIGHT}HỆ THỐNG ĐỒNG BỘ THỜI GIAN PHÂN TÁN{Style.RESET_ALL}{' ' * 11}{Fore.CYAN}║{Style.RESET_ALL}")
    print(f"{Fore.CYAN}║{Style.RESET_ALL}{' ' * 15}{Fore.YELLOW}NTP Client Module{Style.RESET_ALL}{' ' * 22}{Fore.CYAN}║{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'═' * 60}{Style.RESET_ALL}")

    perform_ntp_sync(args.server_ip, args.node_id, args.fake_offset)


if __name__ == "__main__":
    main()
