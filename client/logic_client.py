"""
Logical Clock Client - Lamport Clock & Vector Clock
Chạy trên các máy Client (Node 1-4).
Menu tương tác để tạo sự kiện local, send, view clock state.
"""

import socket
import threading
import json
import time
import argparse
from datetime import datetime

SERVER_PORT = 5001
DASHBOARD_PORT = 8080


def format_time(ts):
    return datetime.fromtimestamp(ts).strftime("%H:%M:%S.%f")[:-3]


def log(level, msg):
    ts = format_time(time.time())
    print(f"[{ts}] [{level}] {msg}")


# ═══════════════════════════════════════════════
# Logical Clock logic
# ═══════════════════════════════════════════════

class LogicalClockClient:
    def __init__(self, server_ip, node_id, total_nodes=5):
        self.server_ip = server_ip
        self.node_id = node_id
        self.total_nodes = total_nodes

        self.lamport_clock = 0
        self.vector_clock = [0] * total_nodes

        self.sock = None
        self.connected = False
        self.buffer = ""

        self.event_history = []

    def connect(self):
        """Kết nối đến Logic Server"""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.server_ip, SERVER_PORT))
            self.connected = True

            register_msg = json.dumps({
                "type": "register",
                "node_id": self.node_id,
                "total_nodes": self.total_nodes,
            }) + "\n"
            self.sock.sendall(register_msg.encode("utf-8"))

            data = self.sock.recv(4096).decode("utf-8")
            for line in data.strip().split("\n"):
                if line.strip():
                    ack = json.loads(line)
                    if ack.get("type") == "registered":
                        log("OK", f"Đã kết nối và đăng ký với Logic Server")

            listener = threading.Thread(target=self._listen_incoming, daemon=True)
            listener.start()

            return True
        except Exception as e:
            log("WARN", f"Không thể kết nối đến Logic Server: {e}")
            return False

    def _listen_incoming(self):
        """Thread lắng nghe message gửi đến từ server (forwarded từ node khác)"""
        while self.connected:
            try:
                data = self.sock.recv(4096).decode("utf-8")
                if not data:
                    break

                self.buffer += data
                while "\n" in self.buffer:
                    line, self.buffer = self.buffer.split("\n", 1)
                    if not line.strip():
                        continue

                    try:
                        message = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    if message.get("type") == "receive_event":
                        self._handle_receive(message)

            except (ConnectionResetError, ConnectionAbortedError, OSError):
                break

    def _handle_receive(self, message):
        """Xử lý sự kiện nhận message từ node khác"""
        from_node = message["from_node"]
        received_lamport = message["lamport_clock"]
        received_vector = message["vector_clock"]
        msg_content = message.get("message", "")

        old_lamport = self.lamport_clock
        old_vector = list(self.vector_clock)

        self.lamport_clock = max(self.lamport_clock, received_lamport) + 1
        for i in range(self.total_nodes):
            self.vector_clock[i] = max(self.vector_clock[i], received_vector[i])
        self.vector_clock[self.node_id] += 1

        log("RECV", f"Message tu Node {from_node}: \"{msg_content}\" | Lamport: {old_lamport} -> {self.lamport_clock} | Vector: {old_vector} -> {self.vector_clock}")

        self._record_event("RECEIVE", f"<- Node {from_node}: \"{msg_content}\"",
                           old_lamport, self.lamport_clock,
                           old_vector, list(self.vector_clock))

        # Gửi ACK về server
        ack_msg = json.dumps({
            "type": "receive_ack",
            "node_id": self.node_id,
            "from_node": from_node,
            "lamport_clock": self.lamport_clock,
            "vector_clock": self.vector_clock,
        }) + "\n"
        try:
            self.sock.sendall(ack_msg.encode("utf-8"))
        except Exception:
            pass

        self._show_menu_prompt()

    def local_event(self):
        """Thực hiện sự kiện nội bộ (local event)"""
        old_lamport = self.lamport_clock
        old_vector = list(self.vector_clock)

        self.lamport_clock += 1
        self.vector_clock[self.node_id] += 1

        log("EVENT", f"LOCAL | Lamport: {old_lamport} -> {self.lamport_clock} | Vector: {old_vector} -> {self.vector_clock}")

        self._record_event("LOCAL", "Sự kiện nội bộ",
                           old_lamport, self.lamport_clock,
                           old_vector, list(self.vector_clock))

        notify = json.dumps({
            "type": "local_event",
            "node_id": self.node_id,
            "lamport_clock": self.lamport_clock,
            "vector_clock": self.vector_clock,
        }) + "\n"
        try:
            self.sock.sendall(notify.encode("utf-8"))
        except Exception:
            pass

    def send_event(self, target_node, message=""):
        """Gửi message đến node khác"""
        if target_node == self.node_id:
            log("WARN", "Không thể gửi message cho chính mình!")
            return

        old_lamport = self.lamport_clock
        old_vector = list(self.vector_clock)

        self.lamport_clock += 1
        self.vector_clock[self.node_id] += 1

        log("SEND", f"SEND -> Node {target_node}: \"{message}\" | Lamport: {old_lamport} -> {self.lamport_clock} | Vector: {old_vector} -> {self.vector_clock}")

        self._record_event("SEND", f"-> Node {target_node}: \"{message}\"",
                           old_lamport, self.lamport_clock,
                           old_vector, list(self.vector_clock))

        send_msg = json.dumps({
            "type": "send_event",
            "node_id": self.node_id,
            "target_node": target_node,
            "lamport_clock": self.lamport_clock,
            "vector_clock": self.vector_clock,
            "message": message,
        }) + "\n"
        try:
            self.sock.sendall(send_msg.encode("utf-8"))
        except Exception as e:
            log("WARN", f"Lỗi gửi: {e}")

    def show_state(self):
        """Hiển thị trạng thái clock hiện tại"""
        print(f"\n--- TRANG THAI NODE {self.node_id} ---")
        print(f"  Lamport Clock : {self.lamport_clock}")
        print(f"  Vector Clock  : {self.vector_clock}")
        print(f"  Tong su kien  : {len(self.event_history)}")
        if self.event_history:
            print(f"  Su kien gan nhat:")
            for evt in self.event_history[-5:]:
                print(f"    {evt['type']:<10} L={evt['new_lamport']} V={evt['new_vector']}")
        print()

    def show_history(self):
        """Hiển thị toàn bộ lịch sử sự kiện"""
        if not self.event_history:
            log("INFO", "Chưa có sự kiện nào.")
            return

        print(f"\n{'#':<4} {'Su kien':<12} {'Lamport':<10} {'-> Lamport':<12} {'Vector Clock'}")
        print(f"{'-' * 70}")
        for i, evt in enumerate(self.event_history, 1):
            print(f"{i:<4} {evt['type']:<12} {evt['old_lamport']:<10} {evt['new_lamport']:<12} {evt['new_vector']}")
        print()

    def _record_event(self, event_type, detail, old_lamport, new_lamport, old_vector, new_vector):
        self.event_history.append({
            "type": event_type,
            "detail": detail,
            "old_lamport": old_lamport,
            "new_lamport": new_lamport,
            "old_vector": old_vector,
            "new_vector": new_vector,
            "timestamp": time.time(),
        })

    def _show_menu_prompt(self):
        """Hiện lại prompt menu"""
        print(f"\n  Chon [1-5]: ", end="", flush=True)

    def close(self):
        self.connected = False
        if self.sock:
            self.sock.close()


# ═══════════════════════════════════════════════
# Interactive Menu
# ═══════════════════════════════════════════════

def run_interactive(client):
    """Menu tương tác chính"""
    while True:
        print(f"\n--- LOGICAL CLOCK NODE {client.node_id} ---")
        print(f"  [1] Local Event (su kien noi bo)")
        print(f"  [2] Send Message -> Node khac")
        print(f"  [3] Xem trang thai Clock")
        print(f"  [4] Xem lich su su kien")
        print(f"  [5] Thoat")

        try:
            choice = input(f"\n  Chon [1-5]: ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if choice == "1":
            client.local_event()

        elif choice == "2":
            try:
                target = int(input(f"  Gui den Node (0-{client.total_nodes - 1}): ").strip())
                if target < 0 or target >= client.total_nodes:
                    log("WARN", f"Node ID phai trong khoang 0-{client.total_nodes - 1}")
                    continue
                msg = input(f"  Noi dung message: ").strip()
                if not msg:
                    msg = f"hello from node {client.node_id}"
                client.send_event(target, msg)
            except ValueError:
                log("WARN", "Vui lòng nhập số hợp lệ")

        elif choice == "3":
            client.show_state()

        elif choice == "4":
            client.show_history()

        elif choice == "5":
            log("INFO", "Đang thoát...")
            break

        else:
            log("WARN", "Vui lòng chọn 1-5")


def main():
    parser = argparse.ArgumentParser(description="Logical Clock Client")
    parser.add_argument("--server-ip", required=True, help="Địa chỉ IP Logic Server")
    parser.add_argument("--node-id", type=int, required=True, choices=[0, 1, 2, 3, 4],
                        help="ID của node (0-4)")
    parser.add_argument("--total-nodes", type=int, default=5, help="Tổng số node (mặc định 5)")
    args = parser.parse_args()

    print(f"\n=== HE THONG DONG BO THOI GIAN PHAN TAN | Logical Clock Client Node {args.node_id} ===\n")

    client = LogicalClockClient(args.server_ip, args.node_id, args.total_nodes)

    log("INFO", f"Đang kết nối đến Logic Server ({args.server_ip}:{SERVER_PORT})...")

    if not client.connect():
        log("WARN", "Không thể kết nối. Vui lòng đảm bảo logic_server.py đang chạy.")
        return

    log("INFO", f"Khoi tao: Lamport=0 Vector={[0] * args.total_nodes}")

    try:
        run_interactive(client)
    except KeyboardInterrupt:
        pass
    finally:
        client.close()
        print(f"\nNode {args.node_id} da tat.\n")


if __name__ == "__main__":
    main()
