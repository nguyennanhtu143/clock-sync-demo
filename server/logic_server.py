"""
Logical Clock Server - Điều phối sự kiện giữa các Node
Quản lý Lamport Clock & Vector Clock
Port: 5001 (TCP)
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
PORT = 5001

# Shared state cho dashboard
logic_events = []
logic_lock = threading.Lock()
connected_nodes = {}
node_connections = {}  # node_id -> conn


def get_timestamp():
    return time.time()


def format_time(ts):
    return datetime.fromtimestamp(ts).strftime("%H:%M:%S.%f")[:-3]


def log(level, msg, color=Fore.WHITE):
    ts = format_time(time.time())
    prefix_map = {
        "INFO": f"{Fore.CYAN}[{ts}] {Fore.GREEN}[LOGIC]{Style.RESET_ALL}",
        "EVENT": f"{Fore.CYAN}[{ts}] {Fore.MAGENTA}[EVENT]{Style.RESET_ALL}",
        "CONN": f"{Fore.CYAN}[{ts}] {Fore.YELLOW}[CONN]{Style.RESET_ALL}",
        "FWD": f"{Fore.CYAN}[{ts}] {Fore.BLUE}[FWD →]{Style.RESET_ALL}",
        "ERROR": f"{Fore.CYAN}[{ts}] {Fore.RED}[ERROR]{Style.RESET_ALL}",
        "SUCCESS": f"{Fore.CYAN}[{ts}] {Fore.GREEN}[  ✓  ]{Style.RESET_ALL}",
    }
    prefix = prefix_map.get(level, f"[{ts}] [{level}]")
    print(f"  {prefix} {color}{msg}{Style.RESET_ALL}")


def print_banner():
    banner = f"""
{Fore.MAGENTA}{'═' * 60}
{Fore.MAGENTA}║{Fore.WHITE}{Back.MAGENTA}{'LOGICAL CLOCK SERVER':^58}{Style.RESET_ALL}{Fore.MAGENTA}║
{Fore.MAGENTA}{'═' * 60}
{Fore.MAGENTA}║{Style.RESET_ALL}  {'Role:':<15} {Fore.YELLOW}Event Coordinator{Style.RESET_ALL}{'':>19}{Fore.MAGENTA}║
{Fore.MAGENTA}║{Style.RESET_ALL}  {'Protocol:':<15} {Fore.YELLOW}TCP{Style.RESET_ALL}{'':>34}{Fore.MAGENTA}║
{Fore.MAGENTA}║{Style.RESET_ALL}  {'Port:':<15} {Fore.YELLOW}{PORT}{Style.RESET_ALL}{'':>33}{Fore.MAGENTA}║
{Fore.MAGENTA}║{Style.RESET_ALL}  {'Algorithms:':<15} {Fore.YELLOW}Lamport Clock + Vector Clock{Style.RESET_ALL}{'':>9}{Fore.MAGENTA}║
{Fore.MAGENTA}{'═' * 60}{Style.RESET_ALL}
"""
    print(banner)


def record_event(event_data):
    """Lưu sự kiện cho dashboard"""
    with logic_lock:
        event_data["timestamp"] = time.time()
        event_data["time_str"] = format_time(time.time())
        logic_events.append(event_data)


def get_logic_events():
    """Trả về danh sách sự kiện cho dashboard"""
    with logic_lock:
        return list(logic_events)


def get_connected_nodes_info():
    """Trả về thông tin các node đang kết nối"""
    with logic_lock:
        return dict(connected_nodes)


def send_to_node(target_node_id, message):
    """Gửi message đến node đích"""
    conn = node_connections.get(target_node_id)
    if conn:
        try:
            data = json.dumps(message) + "\n"
            conn.sendall(data.encode("utf-8"))
            return True
        except Exception as e:
            log("ERROR", f"Không thể gửi đến Node {target_node_id}: {e}")
            return False
    else:
        log("ERROR", f"Node {target_node_id} chưa kết nối!")
        return False


def handle_client(conn, addr):
    """Xử lý kết nối từ một Logic Client"""
    node_id = None
    buffer = ""

    try:
        while True:
            data = conn.recv(4096).decode("utf-8")
            if not data:
                break

            buffer += data
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                if not line.strip():
                    continue

                try:
                    message = json.loads(line)
                except json.JSONDecodeError:
                    continue

                msg_type = message.get("type", "")

                # ── Đăng ký node ──
                if msg_type == "register":
                    node_id = message["node_id"]
                    total_nodes = message.get("total_nodes", 5)

                    with logic_lock:
                        connected_nodes[node_id] = {
                            "ip": addr[0],
                            "port": addr[1],
                            "connected_at": time.time()
                        }
                        node_connections[node_id] = conn

                    log("CONN", f"{Fore.GREEN}Node {node_id}{Style.RESET_ALL} kết nối từ {addr[0]}:{addr[1]}")
                    log("INFO", f"Tổng số node đang kết nối: {Fore.YELLOW}{len(connected_nodes)}{Style.RESET_ALL}")

                    # Gửi xác nhận
                    ack = json.dumps({"type": "registered", "node_id": node_id}) + "\n"
                    conn.sendall(ack.encode("utf-8"))

                # ── Sự kiện LOCAL ──
                elif msg_type == "local_event":
                    src = message["node_id"]
                    lamport = message["lamport_clock"]
                    vector = message["vector_clock"]

                    log("EVENT", f"Node {src} → {Fore.CYAN}LOCAL EVENT{Style.RESET_ALL}")
                    log("INFO", f"  Lamport: {Fore.YELLOW}{lamport}{Style.RESET_ALL} | "
                                f"Vector: {Fore.YELLOW}{vector}{Style.RESET_ALL}")

                    record_event({
                        "type": "local",
                        "node_id": src,
                        "lamport_clock": lamport,
                        "vector_clock": vector,
                    })

                # ── Sự kiện SEND ──
                elif msg_type == "send_event":
                    src = message["node_id"]
                    target = message["target_node"]
                    lamport = message["lamport_clock"]
                    vector = message["vector_clock"]
                    msg_content = message.get("message", "")

                    log("EVENT", f"Node {src} → {Fore.BLUE}SEND{Style.RESET_ALL} → Node {target}")
                    log("INFO", f"  Message: \"{msg_content}\"")
                    log("INFO", f"  Lamport: {Fore.YELLOW}{lamport}{Style.RESET_ALL} | "
                                f"Vector: {Fore.YELLOW}{vector}{Style.RESET_ALL}")

                    record_event({
                        "type": "send",
                        "node_id": src,
                        "target_node": target,
                        "lamport_clock": lamport,
                        "vector_clock": vector,
                        "message": msg_content,
                    })

                    # Forward message đến target node
                    forward_msg = {
                        "type": "receive_event",
                        "from_node": src,
                        "lamport_clock": lamport,
                        "vector_clock": vector,
                        "message": msg_content,
                    }

                    if send_to_node(target, forward_msg):
                        log("FWD", f"Forwarded message từ Node {src} → Node {target}")
                    else:
                        log("ERROR", f"Forward thất bại: Node {target} không online")

                # ── Sự kiện RECEIVE (client report kết quả receive) ──
                elif msg_type == "receive_ack":
                    src = message["node_id"]
                    from_node = message["from_node"]
                    lamport = message["lamport_clock"]
                    vector = message["vector_clock"]

                    log("EVENT", f"Node {src} → {Fore.YELLOW}RECEIVE{Style.RESET_ALL} ← Node {from_node}")
                    log("INFO", f"  Lamport: {Fore.YELLOW}{lamport}{Style.RESET_ALL} | "
                                f"Vector: {Fore.YELLOW}{vector}{Style.RESET_ALL}")

                    record_event({
                        "type": "receive",
                        "node_id": src,
                        "from_node": from_node,
                        "lamport_clock": lamport,
                        "vector_clock": vector,
                    })

                print(f"  {Fore.MAGENTA}{'─' * 58}{Style.RESET_ALL}")

    except (ConnectionResetError, ConnectionAbortedError):
        pass
    except Exception as e:
        log("ERROR", f"Lỗi xử lý Node {node_id}: {e}")
    finally:
        if node_id:
            with logic_lock:
                connected_nodes.pop(node_id, None)
                node_connections.pop(node_id, None)
            log("CONN", f"{Fore.RED}Node {node_id}{Style.RESET_ALL} đã ngắt kết nối")
        conn.close()


def start_server():
    """Khởi động Logic Server"""
    print_banner()

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen(5)

    log("INFO", f"Server đang lắng nghe trên {Fore.GREEN}{HOST}:{PORT}{Style.RESET_ALL}")
    log("INFO", "Đang chờ kết nối từ các Client...")
    print(f"  {Fore.MAGENTA}{'─' * 58}{Style.RESET_ALL}")

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
