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
import sys
from datetime import datetime

from colorama import init, Fore, Style, Back

init(autoreset=True)

SERVER_PORT = 5001
DASHBOARD_PORT = 8080


def format_time(ts):
    return datetime.fromtimestamp(ts).strftime("%H:%M:%S.%f")[:-3]


# ═══════════════════════════════════════════════
# Console UI
# ═══════════════════════════════════════════════

NODE_COLORS = {
    0: Fore.WHITE,
    1: Fore.GREEN,
    2: Fore.YELLOW,
    3: Fore.MAGENTA,
    4: Fore.CYAN,
}


def get_color(node_id):
    return NODE_COLORS.get(node_id, Fore.WHITE)


def log(level, msg):
    ts = format_time(time.time())
    icons = {
        "INFO": f"{Fore.GREEN}ℹ{Style.RESET_ALL}",
        "EVENT": f"{Fore.MAGENTA}⚡{Style.RESET_ALL}",
        "SEND": f"{Fore.BLUE}↑{Style.RESET_ALL}",
        "RECV": f"{Fore.YELLOW}↓{Style.RESET_ALL}",
        "OK": f"{Fore.GREEN}✓{Style.RESET_ALL}",
        "WARN": f"{Fore.YELLOW}⚠{Style.RESET_ALL}",
    }
    icon = icons.get(level, " ")
    print(f"  {Fore.CYAN}[{ts}]{Style.RESET_ALL} {icon} {msg}")


def print_box(lines, title="", color=Fore.MAGENTA, width=56):
    print()
    if title:
        padding = width - len(title) - 4
        left_pad = padding // 2
        right_pad = padding - left_pad
        print(f"  {color}╔{'═' * left_pad} {Style.BRIGHT}{title} {Style.RESET_ALL}{color}{'═' * right_pad}╗{Style.RESET_ALL}")
    else:
        print(f"  {color}╔{'═' * width}╗{Style.RESET_ALL}")
    for line in lines:
        print(f"  {color}║{Style.RESET_ALL} {line:<{width - 2}} {color}║{Style.RESET_ALL}")
    print(f"  {color}╚{'═' * width}╝{Style.RESET_ALL}")
    print()


def print_clock_state(node_id, lamport, vector, event_type="", extra=""):
    """In trạng thái clock đẹp"""
    color = get_color(node_id)
    vector_str = str(vector)

    lines = []
    if event_type:
        lines.append(f"{'Sự kiện:':<20} {Fore.WHITE}{Style.BRIGHT}{event_type}{Style.RESET_ALL}")
    if extra:
        lines.append(f"{'Chi tiết:':<20} {extra}")
    lines.append(f"{'Lamport Clock:':<20} {Fore.YELLOW}{Style.BRIGHT}{lamport}{Style.RESET_ALL}")
    lines.append(f"{'Vector Clock:':<20} {Fore.CYAN}{vector_str}{Style.RESET_ALL}")

    title = f"NODE {node_id} — CLOCK STATE"
    print_box(lines, title=title, color=color)


# ═══════════════════════════════════════════════
# Logical Clock logic
# ═══════════════════════════════════════════════

class LogicalClockClient:
    def __init__(self, server_ip, node_id, total_nodes=5):
        self.server_ip = server_ip
        self.node_id = node_id
        self.total_nodes = total_nodes

        # Lamport Clock
        self.lamport_clock = 0

        # Vector Clock: [node_0, node_1, node_2, node_3, node_4]
        self.vector_clock = [0] * total_nodes

        # Socket kết nối đến Logic Server
        self.sock = None
        self.connected = False
        self.buffer = ""

        # Event history
        self.event_history = []

    def connect(self):
        """Kết nối đến Logic Server"""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.server_ip, SERVER_PORT))
            self.connected = True

            # Đăng ký
            register_msg = json.dumps({
                "type": "register",
                "node_id": self.node_id,
                "total_nodes": self.total_nodes,
            }) + "\n"
            self.sock.sendall(register_msg.encode("utf-8"))

            # Nhận xác nhận
            data = self.sock.recv(4096).decode("utf-8")
            # Parse ack
            for line in data.strip().split("\n"):
                if line.strip():
                    ack = json.loads(line)
                    if ack.get("type") == "registered":
                        log("OK", f"Đã kết nối và đăng ký với Logic Server")

            # Bắt đầu thread lắng nghe message đến
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

        # Cập nhật Lamport Clock: LC = max(LC, received_LC) + 1
        self.lamport_clock = max(self.lamport_clock, received_lamport) + 1

        # Cập nhật Vector Clock:
        # VC[i] = max(VC[i], received_VC[i]) for all i, then VC[self] += 1
        for i in range(self.total_nodes):
            self.vector_clock[i] = max(self.vector_clock[i], received_vector[i])
        self.vector_clock[self.node_id] += 1

        print(f"\n  {Fore.YELLOW}{'!' * 50}{Style.RESET_ALL}")
        print(f"  {Fore.YELLOW}  📨 MESSAGE NHẬN TỪ NODE {from_node}: \"{msg_content}\"{Style.RESET_ALL}")
        log("RECV", f"Nhận message từ Node {from_node}")
        log("INFO", f"  Lamport: {old_lamport} → {Fore.YELLOW}{self.lamport_clock}{Style.RESET_ALL}")
        log("INFO", f"  Vector:  {old_vector} → {Fore.CYAN}{self.vector_clock}{Style.RESET_ALL}")

        self._record_event("RECEIVE", f"← Node {from_node}: \"{msg_content}\"",
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

        print_clock_state(self.node_id, self.lamport_clock, self.vector_clock,
                          "RECEIVE", f"← Node {from_node}: \"{msg_content}\"")
        self._show_menu_prompt()

    def local_event(self):
        """Thực hiện sự kiện nội bộ (local event)"""
        old_lamport = self.lamport_clock
        old_vector = list(self.vector_clock)

        # Lamport: LC += 1
        self.lamport_clock += 1

        # Vector: VC[self] += 1
        self.vector_clock[self.node_id] += 1

        log("EVENT", f"Sự kiện LOCAL")
        log("INFO", f"  Lamport: {old_lamport} → {Fore.YELLOW}{self.lamport_clock}{Style.RESET_ALL}")
        log("INFO", f"  Vector:  {old_vector} → {Fore.CYAN}{self.vector_clock}{Style.RESET_ALL}")

        self._record_event("LOCAL", "Sự kiện nội bộ",
                           old_lamport, self.lamport_clock,
                           old_vector, list(self.vector_clock))

        # Thông báo server
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

        print_clock_state(self.node_id, self.lamport_clock, self.vector_clock,
                          "LOCAL EVENT", "Sự kiện nội bộ")

    def send_event(self, target_node, message=""):
        """Gửi message đến node khác"""
        if target_node == self.node_id:
            log("WARN", "Không thể gửi message cho chính mình!")
            return

        old_lamport = self.lamport_clock
        old_vector = list(self.vector_clock)

        # Lamport: LC += 1
        self.lamport_clock += 1

        # Vector: VC[self] += 1
        self.vector_clock[self.node_id] += 1

        log("SEND", f"Gửi message → Node {target_node}: \"{message}\"")
        log("INFO", f"  Lamport: {old_lamport} → {Fore.YELLOW}{self.lamport_clock}{Style.RESET_ALL}")
        log("INFO", f"  Vector:  {old_vector} → {Fore.CYAN}{self.vector_clock}{Style.RESET_ALL}")

        self._record_event("SEND", f"→ Node {target_node}: \"{message}\"",
                           old_lamport, self.lamport_clock,
                           old_vector, list(self.vector_clock))

        # Gửi đến server để forward
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

        print_clock_state(self.node_id, self.lamport_clock, self.vector_clock,
                          "SEND EVENT", f"→ Node {target_node}: \"{message}\"")

    def show_state(self):
        """Hiển thị trạng thái clock hiện tại"""
        lines = [
            f"{'Lamport Clock:':<20} {Fore.YELLOW}{Style.BRIGHT}{self.lamport_clock}{Style.RESET_ALL}",
            f"{'Vector Clock:':<20} {Fore.CYAN}{self.vector_clock}{Style.RESET_ALL}",
            f"{'─' * 54}",
            f"{'Tổng sự kiện:':<20} {len(self.event_history)}",
        ]

        if self.event_history:
            lines.append(f"{'─' * 54}")
            lines.append(f"{Fore.WHITE}{Style.BRIGHT}{'Lịch sử sự kiện gần nhất:'}{Style.RESET_ALL}")
            for evt in self.event_history[-5:]:
                lines.append(f"  {evt['type']:<10} L={evt['new_lamport']} V={evt['new_vector']}")

        print_box(lines, f"TRẠNG THÁI NODE {self.node_id}", get_color(self.node_id))

    def show_history(self):
        """Hiển thị toàn bộ lịch sử sự kiện"""
        if not self.event_history:
            log("INFO", "Chưa có sự kiện nào.")
            return

        print(f"\n  {Fore.MAGENTA}{'═' * 75}{Style.RESET_ALL}")
        print(f"  {Fore.WHITE}{Style.BRIGHT}{'#':<4} {'Sự kiện':<12} {'Lamport':>8} {'→':>3} {'Lamport':>8} {'Vector Clock':<30}{Style.RESET_ALL}")
        print(f"  {Fore.MAGENTA}{'─' * 75}{Style.RESET_ALL}")

        for i, evt in enumerate(self.event_history, 1):
            evt_color = {
                "LOCAL": Fore.CYAN,
                "SEND": Fore.BLUE,
                "RECEIVE": Fore.YELLOW,
            }.get(evt["type"], Fore.WHITE)

            print(f"  {Fore.WHITE}{i:<4}{Style.RESET_ALL} "
                  f"{evt_color}{evt['type']:<12}{Style.RESET_ALL} "
                  f"{evt['old_lamport']:>8} {Fore.WHITE}→{Style.RESET_ALL} "
                  f"{Fore.YELLOW}{evt['new_lamport']:>8}{Style.RESET_ALL} "
                  f"{Fore.CYAN}{str(evt['new_vector']):<30}{Style.RESET_ALL}")

        print(f"  {Fore.MAGENTA}{'═' * 75}{Style.RESET_ALL}\n")

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
        print(f"\n  {Fore.WHITE}Chọn [1-5]: {Style.RESET_ALL}", end="", flush=True)

    def close(self):
        self.connected = False
        if self.sock:
            self.sock.close()


# ═══════════════════════════════════════════════
# Interactive Menu
# ═══════════════════════════════════════════════

def run_interactive(client):
    """Menu tương tác chính"""
    color = get_color(client.node_id)

    while True:
        print(f"\n  {color}{'═' * 45}{Style.RESET_ALL}")
        print(f"  {color}║{Style.RESET_ALL} {Fore.WHITE}{Style.BRIGHT}LOGICAL CLOCK — NODE {client.node_id}{Style.RESET_ALL}{'':>{22 - len(str(client.node_id))}}{color}║{Style.RESET_ALL}")
        print(f"  {color}{'═' * 45}{Style.RESET_ALL}")
        print(f"  {color}║{Style.RESET_ALL}  {Fore.CYAN}[1]{Style.RESET_ALL} Local Event (sự kiện nội bộ)     {color}║{Style.RESET_ALL}")
        print(f"  {color}║{Style.RESET_ALL}  {Fore.BLUE}[2]{Style.RESET_ALL} Send Message → Node khác         {color}║{Style.RESET_ALL}")
        print(f"  {color}║{Style.RESET_ALL}  {Fore.YELLOW}[3]{Style.RESET_ALL} Xem trạng thái Clock            {color}║{Style.RESET_ALL}")
        print(f"  {color}║{Style.RESET_ALL}  {Fore.MAGENTA}[4]{Style.RESET_ALL} Xem lịch sử sự kiện            {color}║{Style.RESET_ALL}")
        print(f"  {color}║{Style.RESET_ALL}  {Fore.RED}[5]{Style.RESET_ALL} Thoát                            {color}║{Style.RESET_ALL}")
        print(f"  {color}{'═' * 45}{Style.RESET_ALL}")

        try:
            choice = input(f"\n  {Fore.WHITE}Chọn [1-5]: {Style.RESET_ALL}").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if choice == "1":
            client.local_event()

        elif choice == "2":
            try:
                target = int(input(f"  {Fore.BLUE}Gửi đến Node (0-{client.total_nodes - 1}): {Style.RESET_ALL}").strip())
                if target < 0 or target >= client.total_nodes:
                    log("WARN", f"Node ID phải trong khoảng 0-{client.total_nodes - 1}")
                    continue
                msg = input(f"  {Fore.BLUE}Nội dung message: {Style.RESET_ALL}").strip()
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

    color = get_color(args.node_id)
    print(f"\n{color}{'═' * 60}{Style.RESET_ALL}")
    print(f"{color}║{Style.RESET_ALL}{' ' * 10}{Fore.WHITE}{Style.BRIGHT}HỆ THỐNG ĐỒNG BỘ THỜI GIAN PHÂN TÁN{Style.RESET_ALL}{' ' * 11}{color}║{Style.RESET_ALL}")
    print(f"{color}║{Style.RESET_ALL}{' ' * 12}{Fore.MAGENTA}Logical Clock Client Module{Style.RESET_ALL}{' ' * 19}{color}║{Style.RESET_ALL}")
    print(f"{color}{'═' * 60}{Style.RESET_ALL}")

    client = LogicalClockClient(args.server_ip, args.node_id, args.total_nodes)

    log("INFO", f"Đang kết nối đến Logic Server ({args.server_ip}:{SERVER_PORT})...")

    if not client.connect():
        log("WARN", "Không thể kết nối. Vui lòng đảm bảo logic_server.py đang chạy.")
        return

    print_clock_state(args.node_id, 0, [0] * args.total_nodes, "KHỞI TẠO", "Đã kết nối")

    try:
        run_interactive(client)
    except KeyboardInterrupt:
        pass
    finally:
        client.close()
        print(f"\n  {Fore.GREEN}✓ Node {args.node_id} đã tắt.{Style.RESET_ALL}\n")


if __name__ == "__main__":
    main()
