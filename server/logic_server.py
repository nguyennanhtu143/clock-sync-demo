"""
Logical Clock Server - Điều phối sự kiện giữa các Node
Quản lý Lamport Clock & Vector Clock
Port: 5001 (TCP)
"""

import socket
import threading
import json
import time
from datetime import datetime

HOST = "0.0.0.0"
PORT = 5001

# Shared state cho dashboard
logic_events = []
logic_lock = threading.Lock()
connected_nodes = {}
node_connections = {}  # node_id -> conn

# Callback để emit SocketIO — được set bởi dashboard.py
_emit_callback = None


def set_emit_callback(callback):
    """Dashboard gọi hàm này để đăng ký callback emit SocketIO"""
    global _emit_callback
    _emit_callback = callback


def get_timestamp():
    return time.time()


def format_time(ts):
    return datetime.fromtimestamp(ts).strftime("%H:%M:%S.%f")[:-3]


def log(level, msg):
    ts = format_time(time.time())
    print(f"[{ts}] [{level}] {msg}")


def record_event(event_data):
    """Lưu sự kiện cho dashboard và emit real-time"""
    with logic_lock:
        event_data["timestamp"] = time.time()
        event_data["time_str"] = format_time(time.time())
        logic_events.append(event_data)
    if _emit_callback:
        try:
            _emit_callback("logic_update", dict(event_data))
        except Exception as e:
            log("ERROR", f"Emit callback lỗi: {e}")


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

                    log("CONN", f"Node {node_id} kết nối từ {addr[0]}:{addr[1]} | Tổng: {len(connected_nodes)} node")

                    ack = json.dumps({"type": "registered", "node_id": node_id}) + "\n"
                    conn.sendall(ack.encode("utf-8"))

                # ── Sự kiện LOCAL ──
                elif msg_type == "local_event":
                    src = message["node_id"]
                    lamport = message["lamport_clock"]
                    vector = message["vector_clock"]

                    log("EVENT", f"Node {src} LOCAL | Lamport={lamport} Vector={vector}")

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

                    log("EVENT", f"Node {src} SEND -> Node {target} | Lamport={lamport} msg=\"{msg_content}\"")

                    record_event({
                        "type": "send",
                        "node_id": src,
                        "target_node": target,
                        "lamport_clock": lamport,
                        "vector_clock": vector,
                        "message": msg_content,
                    })

                    forward_msg = {
                        "type": "receive_event",
                        "from_node": src,
                        "lamport_clock": lamport,
                        "vector_clock": vector,
                        "message": msg_content,
                    }

                    if not send_to_node(target, forward_msg):
                        log("ERROR", f"Forward thất bại: Node {target} không online")

                # ── Sự kiện RECEIVE (client report kết quả receive) ──
                elif msg_type == "receive_ack":
                    src = message["node_id"]
                    from_node = message["from_node"]
                    lamport = message["lamport_clock"]
                    vector = message["vector_clock"]

                    log("EVENT", f"Node {src} RECEIVE <- Node {from_node} | Lamport={lamport} Vector={vector}")

                    record_event({
                        "type": "receive",
                        "node_id": src,
                        "from_node": from_node,
                        "lamport_clock": lamport,
                        "vector_clock": vector,
                    })

    except (ConnectionResetError, ConnectionAbortedError):
        pass
    except Exception as e:
        log("ERROR", f"Lỗi xử lý Node {node_id}: {e}")
    finally:
        if node_id:
            with logic_lock:
                connected_nodes.pop(node_id, None)
                node_connections.pop(node_id, None)
            log("CONN", f"Node {node_id} ngắt kết nối")
        conn.close()


def start_server():
    """Khởi động Logic Server"""
    print(f"=== LOGICAL CLOCK SERVER | Port {PORT} | Lamport + Vector Clock ===")

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
