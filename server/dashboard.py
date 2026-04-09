"""
Dashboard Web Server — Hiển thị trực quan kết quả đồng bộ
Chạy trên máy Server, cung cấp giao diện web tại Port 8080.
Tích hợp dữ liệu từ NTP Server và Logic Server.
"""

import threading
import json
import time
import sys
import os
from datetime import datetime

from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO

from colorama import init, Fore, Style

init(autoreset=True)

# ═══════════════════════════════════════════════
# Flask App
# ═══════════════════════════════════════════════

app = Flask(__name__)
app.config["SECRET_KEY"] = "htpt-dashboard-2026"
socketio = SocketIO(app, cors_allowed_origins="*")

# ═══════════════════════════════════════════════
# Shared State
# ═══════════════════════════════════════════════

# NTP results from clients
ntp_results = {}    # node_id -> {data}
ntp_lock = threading.Lock()

# Logic events
logic_events = []   # list of event dicts
logic_lock = threading.Lock()

# Connected nodes info
connected_nodes = {}

# Server start time
start_time = time.time()


def format_time(ts):
    return datetime.fromtimestamp(ts).strftime("%H:%M:%S.%f")[:-3]


def log(level, msg):
    ts = format_time(time.time())
    icons = {
        "INFO": f"{Fore.GREEN}ℹ{Style.RESET_ALL}",
        "API": f"{Fore.BLUE}⚡{Style.RESET_ALL}",
        "WEB": f"{Fore.CYAN}🌐{Style.RESET_ALL}",
    }
    icon = icons.get(level, " ")
    print(f"  {Fore.CYAN}[{ts}]{Style.RESET_ALL} {icon} {Fore.WHITE}[DASHBOARD]{Style.RESET_ALL} {msg}")


# ═══════════════════════════════════════════════
# Routes
# ═══════════════════════════════════════════════

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/status")
def api_status():
    """Trả về trạng thái hệ thống"""
    with ntp_lock:
        ntp_data = dict(ntp_results)
    with logic_lock:
        events = list(logic_events)

    return jsonify({
        "server_time": time.time(),
        "server_time_str": format_time(time.time()),
        "uptime": time.time() - start_time,
        "ntp_results": ntp_data,
        "logic_events": events,
        "connected_nodes": len(ntp_data),
    })


@app.route("/api/ntp/result", methods=["POST"])
def api_ntp_result():
    """Nhận kết quả NTP từ client"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data"}), 400

    node_id = str(data.get("node_id", "?"))

    with ntp_lock:
        ntp_results[node_id] = {
            **data,
            "received_at": time.time(),
            "received_at_str": format_time(time.time()),
        }

    log("API", f"NTP result từ {Fore.YELLOW}Node {node_id}{Style.RESET_ALL} | "
              f"Offset: {data.get('offset', 0):+.6f}s | "
              f"Delay: {data.get('delay', 0) * 1000:.1f}ms")

    # Broadcast to dashboard via SocketIO
    socketio.emit("ntp_update", {
        "node_id": node_id,
        "data": ntp_results[node_id]
    })

    return jsonify({"status": "ok"})


@app.route("/api/logic/event", methods=["POST"])
def api_logic_event():
    """Nhận sự kiện Logic Clock"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data"}), 400

    data["received_at"] = time.time()
    data["received_at_str"] = format_time(time.time())

    with logic_lock:
        logic_events.append(data)

    log("API", f"Logic event: {data.get('type', '?')} từ Node {data.get('node_id', '?')}")

    # Broadcast to dashboard
    socketio.emit("logic_update", data)

    return jsonify({"status": "ok"})


@app.route("/api/ntp/results")
def api_ntp_results():
    """Trả về tất cả kết quả NTP"""
    with ntp_lock:
        return jsonify(dict(ntp_results))


@app.route("/api/logic/events")
def api_logic_events():
    """Trả về tất cả sự kiện Logic"""
    with logic_lock:
        return jsonify(list(logic_events))


# ═══════════════════════════════════════════════
# NTP + Logic Server Integration
# ═══════════════════════════════════════════════

def start_ntp_server_thread():
    """Chạy NTP Server trong thread riêng"""
    sys.path.insert(0, os.path.dirname(__file__))
    from ntp_server import start_server as ntp_start
    thread = threading.Thread(target=ntp_start, daemon=True)
    thread.start()
    log("INFO", f"NTP Server đã khởi động trên {Fore.GREEN}Port 5000{Style.RESET_ALL}")
    return thread


def start_logic_server_thread():
    """Chạy Logic Server trong thread riêng"""
    sys.path.insert(0, os.path.dirname(__file__))
    from logic_server import start_server as logic_start
    thread = threading.Thread(target=logic_start, daemon=True)
    thread.start()
    log("INFO", f"Logic Server đã khởi động trên {Fore.GREEN}Port 5001{Style.RESET_ALL}")
    return thread


# ═══════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════

def print_banner():
    banner = f"""
{Fore.WHITE}{'═' * 60}
{Fore.WHITE}║{Fore.WHITE}{Style.BRIGHT}{'DISTRIBUTED TIME SYNC — DASHBOARD':^58}{Style.RESET_ALL}{Fore.WHITE}║
{Fore.WHITE}{'═' * 60}
{Fore.WHITE}║{Style.RESET_ALL}  NTP Server ............. {Fore.GREEN}Port 5000{Style.RESET_ALL}{'':>18}{Fore.WHITE}║
{Fore.WHITE}║{Style.RESET_ALL}  Logic Server ........... {Fore.GREEN}Port 5001{Style.RESET_ALL}{'':>18}{Fore.WHITE}║
{Fore.WHITE}║{Style.RESET_ALL}  Web Dashboard .......... {Fore.GREEN}Port 8080{Style.RESET_ALL}{'':>18}{Fore.WHITE}║
{Fore.WHITE}║{Style.RESET_ALL}  {Fore.CYAN}→ http://0.0.0.0:8080{Style.RESET_ALL}{'':>31}{Fore.WHITE}║
{Fore.WHITE}{'═' * 60}{Style.RESET_ALL}
"""
    print(banner)


if __name__ == "__main__":
    print_banner()

    # Khởi động NTP Server
    start_ntp_server_thread()
    time.sleep(0.5)

    # Khởi động Logic Server
    start_logic_server_thread()
    time.sleep(0.5)

    # Khởi động Dashboard
    log("INFO", f"Dashboard đang chạy tại {Fore.GREEN}http://0.0.0.0:8080{Style.RESET_ALL}")
    log("INFO", "Mở browser để xem dashboard")

    socketio.run(app, host="0.0.0.0", port=8080, debug=False, allow_unsafe_werkzeug=True)
