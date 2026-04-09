"""
MAIN SERVER 

Responsibilities:
  - Receive UDP packets from the sensors
  - Track the previous state of each cat/sensor (to detect actual state changes)
  - Call the actuator ONLY when there is a state change (False→True)
  - Apply the actions returned by the actuators (blocking, resetting, alerting)
  - Forward actuator messages to the interface
"""

import random
import json
import os
import socket
import threading
from datetime import datetime
import queue
from concurrent.futures import ThreadPoolExecutor

import os
HOST                  = os.environ.get("BIND_HOST", "0.0.0.0")
PORT_APP              = int(os.environ.get("APP_PORT",            2005))
PORT_SENSOR           = int(os.environ.get("SENSOR_PORT",         2001))
ATUATOR_ACCESS_HOST   = os.environ.get("ATUATOR_ACCESS_HOST",   "kitty_atuador_access")
ATUATOR_ACCESS_PORT   = int(os.environ.get("ATUATOR_ACCESS_PORT", 2000))
ATUATOR_WELFARE_HOST  = os.environ.get("ATUATOR_WELFARE_HOST",  "kitty_atuador_welfare")
ATUATOR_WELFARE_PORT  = int(os.environ.get("ATUATOR_WELFARE_PORT", 2003))

LOGS_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

CAT_JSON_FILE = os.path.join(os.path.dirname(__file__), "..", "interface", "cats.json")

interface_clients = []
clients_lock      = threading.Lock()
cat_stats         = {}
cat_states        = {}

# ── Producer-consumer to decouple UDP reception from processing ──────
# The main loop only queues raw packets (fast operation).
# A pool of workers processes each packet concurrently.
# Without this, actuator_conn.call() blocks recvfrom() and packets accumulate
# in the OS buffer until they are discarded.
_packet_queue: queue.Queue = queue.Queue(maxsize=2000)

# Per-cat lock: prevents two workers from processing the same cat simultaneously
# (which would cause double-counting of events).
_cat_locks: dict = {}
_cat_locks_mutex = threading.Lock()

def _get_cat_lock(cat_name: str) -> threading.Lock:
    """Returns (creating if necessary) the exclusive lock for a cat."""
    with _cat_locks_mutex:
        if cat_name not in _cat_locks:
            _cat_locks[cat_name] = threading.Lock()
        return _cat_locks[cat_name]

# Minimum time (seconds) for two events from the same sensor/cat
# to be recognized as DISTINCT events.
# Solves the sensor alternating True/False every 0.001s problem:
# a 30-second bathroom visit won't turn into 15,000 counts.
# Adjust according to the realistic minimum duration of each event in the simulation.
# Minimum interval (seconds) between SUBTLE alerts sent to the interface
# for the same (cat, sensor). Avoids flooding with "tried to leave but door is blocked" messages.
SUBTLE_THROTTLE = {
    "door":    21,
    "window":  21,
    "food":    21,
    "bed":     20,
    "sandbox": 20,
}

# Asynchronous queue for log writing (does not block the main loop)
_log_queue: queue.Queue = queue.Queue(maxsize=500)

def _log_worker():
    """Dedicated thread for log writing — continuously consumes the queue."""
    while True:
        try:
            path, record = _log_queue.get(timeout=2)
            dados = []
            if os.path.exists(path):
                try:
                    with open(path) as f:
                        dados = json.load(f)
                except Exception:
                    dados = []
            dados.append(record)
            # Keeps a maximum of 500 entries per log file
            if len(dados) > 500:
                dados = dados[-500:]
            with open(path, "w") as f:
                json.dump(dados, f, indent=2)
            _log_queue.task_done()
        except queue.Empty:
            pass
        except Exception as e:
            print(f"[LOG-WORKER] {e}")

threading.Thread(target=_log_worker, daemon=True).start()

MIN_EVENT_INTERVAL = {
    "door":    2,    # an exit lasts at least 2s
    "window":  2,
    "food":    5,    # a meal lasts at least 5s
    "bed":    10,    # a nap lasts at least 10s
    "sandbox": 10,   # a bathroom visit lasts at least 10s
}


# ══════════════════════════════════════════════
# Communication with Actuators
# ══════════════════════════════════════════════

class AtuatorConnection:
    def __init__(self, host, port):
        self.host    = host
        self.port    = port
        self._sock   = None
        self._buffer = ""
        self._lock   = threading.Lock()

    def _connect(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((self.host, self.port))
        self._sock   = s
        self._buffer = ""
        print(f"[SERVER] Connected to actuator {self.host}:{self.port}")

    def _ensure(self):
        if self._sock is None:
            self._connect()

    def call(self, sensor_type: str, params: dict) -> dict:
        with self._lock:
            for attempt in range(2):
                try:
                    self._ensure()
                    msg = json.dumps({"sensor_type": sensor_type, "params": params}, ensure_ascii=False) + "\n"
                    self._sock.sendall(msg.encode())
                    while "\n" not in self._buffer:
                        chunk = self._sock.recv(4096)
                        if not chunk:
                            raise ConnectionResetError()
                        self._buffer += chunk.decode()
                    line, self._buffer = self._buffer.split("\n", 1)
                    return json.loads(line)
                except Exception as e:
                    print(f"[SERVER] Actuator error (attempt {attempt+1}): {e}")
                    try: self._sock.close()
                    except: pass
                    self._sock   = None
                    self._buffer = ""
            return {"action": None, "message": None, "reset_count": False}


atuator_access_conn  = AtuatorConnection(ATUATOR_ACCESS_HOST,  ATUATOR_ACCESS_PORT)
atuator_welfare_conn = AtuatorConnection(ATUATOR_WELFARE_HOST, ATUATOR_WELFARE_PORT)


# ══════════════════════════════════════════════
# Per-cat state
# ══════════════════════════════════════════════

def _init_cat(cat_name: str):
    """
    Initializes the state of a cat.

    prev_*  → last cat_state received per sensor.
              The server only calls the actuator when this value changes
              (False/None → True). This ensures each physical event
              is counted exactly once, regardless of how many UDP
              packets the sensor emits per second.

    *_count → daily event counter, reset by the actuator after a
              critical action or owner confirmation in the interface.

    *_blocked → blocking flag. When True, the sensor keeps detecting,
                but the actuator only notifies attempts.
    """
    cat_states[cat_name] = {
        # counters
        "door_count":    0,
        "window_count":  0,
        "food_count":    0,
        "bed_count":     0,
        "sandbox_count": 0,

        # mutual exclusion flag: while True, door/window/food sensors are ignored
        "bed_occupied": False,

        # blocks (door, window and food can be blocked)
        "door_blocked":    False,
        "window_blocked":  False,
        "food_blocked":    False,

        # previous state per sensor (False→True transition control)
        "prev_door":    None,
        "prev_window":  None,
        "prev_food":    None,
        "prev_bed":     None,
        "prev_sandbox": None,

        # timestamp of the last COUNTED event per sensor.
        # Prevents the sensor's rapid True/False alternation
        # (every 0.001s) from generating multiple counts for the
        # same physical event. Two consecutive Trues only become two
        # distinct events if the time between them is >= MIN_EVENT_INTERVAL.
        "last_event_door":    None,
        "last_event_window":  None,
        "last_event_food":    None,
        "last_event_bed":     None,
        "last_event_sandbox": None,

        # timestamp of the last SUBTLE alert sent to the interface (per sensor).
        # Avoids flooding with attempt messages when a device is blocked.
        "last_subtle_door":    None,
        "last_subtle_window":  None,
        "last_subtle_food":    None,
        "last_subtle_bed":     None,
        "last_subtle_sandbox": None,
    }


def is_new_event(cat_name: str, sensor_key: str, current: bool) -> bool:
    """
    Returns True only when:
      1. The current state is True (sensor active)
      2. The previous state was False or None (real transition)
      3. Enough time has passed since the last counted event (MIN_EVENT_INTERVAL)

    Conditions 1+2 alone are not enough because the sensor alternates
    True/False every 0.001s while the event is active — generating
    hundreds of "rising edges" per second for a single physical event.
    Condition 3 ensures that two Trues separated by less than N seconds
    are treated as the same event, not as distinct events.
    """
    if not current:
        cat_states[cat_name][f"prev_{sensor_key}"] = current
        return False

    prev     = cat_states[cat_name].get(f"prev_{sensor_key}")
    last     = cat_states[cat_name].get(f"last_event_{sensor_key}")
    now      = datetime.now()
    interval = MIN_EVENT_INTERVAL.get(sensor_key, 2)

    cat_states[cat_name][f"prev_{sensor_key}"] = current

    # It's a new event if: never counted before OR enough time has passed
    if last is None or (now - last).total_seconds() >= interval:
        cat_states[cat_name][f"last_event_{sensor_key}"] = now
        return True

    return False


# ══════════════════════════════════════════════
# Interface
# ══════════════════════════════════════════════

def _can_send_subtle(cat: str, sensor_key: str) -> bool:
    """
    Returns True if enough time has passed since the last subtle alert
    sent for this (cat, sensor). Throttle independent of MIN_EVENT_INTERVAL:
    even if is_new_event releases a new event, the subtle alert only reaches
    the interface if the owner has not been notified recently.
    """
    state_key = f"last_subtle_{sensor_key}"
    if cat not in cat_states:
        return True
    last = cat_states[cat].get(state_key)
    now  = datetime.now()
    limit = SUBTLE_THROTTLE.get(sensor_key, 15)
    if last is None or (now - last).total_seconds() >= limit:
        cat_states[cat][state_key] = now
        return True
    return False


def send_interface_alert(alert: dict):
    with clients_lock:
        dead = []
        for conn in interface_clients:
            try:
                conn.sendall((json.dumps(alert, ensure_ascii=False) + "\n").encode())
            except:
                dead.append(conn)
        for conn in dead:
            try: conn.close()
            except: pass
            interface_clients.remove(conn)


def handle_command(cmd: dict):
    """
    Processes commands coming from the interface (owner's app).

    open_door / open_window / unblock_food:
      The owner decided to reopen the device. The server unblocks
      it and resets the counter so the cycle starts from zero.

    ok_bed / ok_sandbox:
      The owner confirmed ('ok') the bed/sandbox alert.
      The server only resets the counter.
    """
    command = cmd.get("command")
    cat     = cmd.get("cat")
    if cat not in cat_states:
        return

    if command == "open_door":
        cat_states[cat]["door_blocked"] = False
        cat_states[cat]["door_count"]   = 0
        send_interface_alert({"message": f"Door reopened for {cat}.", "subtle": False, "timestamp": datetime.now().isoformat()})

    elif command == "open_window":
        cat_states[cat]["window_blocked"] = False
        cat_states[cat]["window_count"]   = 0
        send_interface_alert({"message": f"Window reopened for {cat}.", "subtle": False, "timestamp": datetime.now().isoformat()})

    elif command == "unblock_food":
        cat_states[cat]["food_blocked"] = False
        cat_states[cat]["food_count"]   = 0
        send_interface_alert({"message": f"Dispenser reopened for {cat}.", "subtle": False, "timestamp": datetime.now().isoformat()})

    elif command == "close_door":
        cat_states[cat]["door_blocked"] = True
        send_interface_alert({"message": f"Door manually closed for {cat}.", "subtle": True, "timestamp": datetime.now().isoformat()})

    elif command == "close_window":
        cat_states[cat]["window_blocked"] = True
        send_interface_alert({"message": f"Window manually closed for {cat}.", "subtle": True, "timestamp": datetime.now().isoformat()})

    elif command == "block_food":
        cat_states[cat]["food_blocked"] = True
        send_interface_alert({"message": f"Dispenser manually blocked for {cat}.", "subtle": True, "timestamp": datetime.now().isoformat()})

    elif command in ("ok_bed", "ok_sandbox"):
        sensor = command.replace("ok_", "")
        cat_states[cat][f"{sensor}_count"] = 0
        send_interface_alert({"message": f"{sensor} counter reset for {cat}.", "subtle": True, "timestamp": datetime.now().isoformat()})


def handle_interface_client(conn, addr):
    print(f"[SERVER] Interface connected: {addr}")
    with clients_lock:
        interface_clients.append(conn)
    buf = ""
    try:
        while True:
            data = conn.recv(1024)
            if not data:
                break
            buf += data.decode()
            while "\n" in buf:
                line, buf = buf.split("\n", 1)
                try: handle_command(json.loads(line))
                except json.JSONDecodeError: pass
    except Exception as e:
        print(f"[SERVER] Interface error: {e}")
    finally:
        with clients_lock:
            if conn in interface_clients:
                interface_clients.remove(conn)
        try: conn.close()
        except: pass


def accept_interface_clients(sock):
    while True:
        conn, addr = sock.accept()
        threading.Thread(target=handle_interface_client, args=(conn, addr), daemon=True).start()


# ══════════════════════════════════════════════
# Logs
# ══════════════════════════════════════════════

def get_log_path(f): return os.path.join(LOGS_DIR, f)

def _append_log(path, record):
    """Queues the record for asynchronous writing — does not block the loop."""
    try:
        _log_queue.put_nowait((path, record))
    except queue.Full:
        pass  # discard if queue is full (overload protection)

def update_cat_stats(cat_name, sensor_type):
    if cat_name not in cat_stats:
        cat_stats[cat_name] = {"door": 0, "window": 0, "food": 0, "sandbox": 0, "bed": 0}
    if sensor_type in cat_stats[cat_name]:
        cat_stats[cat_name][sensor_type] += 1
    try:
        with open(get_log_path("cat_activity.json"), "w", encoding="utf-8") as f:
            json.dump(cat_stats, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Stats error: {e}")


# ══════════════════════════════════════════════
# Main loop
# ══════════════════════════════════════════════

def initialize_server():
    sensor_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sensor_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sensor_sock.bind((HOST, PORT_SENSOR))

    app_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    app_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    app_sock.bind((HOST, PORT_APP))
    app_sock.listen()

    threading.Thread(target=accept_interface_clients, args=(app_sock,), daemon=True).start()

    print(f"[SERVER] UDP sensors        → {HOST}:{PORT_SENSOR}")
    print(f"[SERVER] TCP interface      → {HOST}:{PORT_APP}")
    print(f"[SERVER] TCP access actuator→ {ATUATOR_ACCESS_HOST}:{ATUATOR_ACCESS_PORT}")
    print(f"[SERVER] TCP welfare actuator→{ATUATOR_WELFARE_HOST}:{ATUATOR_WELFARE_PORT}")

    # Worker pool: processes UDP packets concurrently.
    # Size = 10 workers — enough for multiple simultaneous cats
    # without creating too many threads (each actuator call blocks ~1-5ms).
    executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix="pkt-worker")

    def _worker_loop():
        """Each worker continuously consumes packets from the queue."""
        while True:
            try:
                packet = _packet_queue.get(timeout=1)
                _process_packet(packet)
                _packet_queue.task_done()
            except queue.Empty:
                pass
            except Exception as e:
                print(f"[WORKER] Unexpected error: {e}")

    # Start workers as daemon threads
    for _ in range(10):
        threading.Thread(target=_worker_loop, daemon=True).start()

    print(f"[SERVER] Pool of 10 workers started for packet processing")

    # Main loop: ONLY receives and queues — never blocks on I/O
    while True:
        packet, _ = sensor_sock.recvfrom(2048)
        try:
            _packet_queue.put_nowait(packet)
        except queue.Full:
            pass  # discard if queue is full (extreme overload)


def _process_packet(packet: bytes):
    """
    Processes a UDP packet in a worker thread.
    Uses a per-cat lock to ensure two workers never process
    the same cat simultaneously (prevents double-counting of events).
    """
    try:
        data      = json.loads(packet.decode())
        sid       = data.get("sensorID")
        cat       = data.get("cat_name", "unknown")
        cat_state = data.get("cat_state")

        if not cat or not cat.strip():
            return

        cat = cat.strip().lower()

        # Ensures the cat state exists (with minimal global lock)
        if cat not in cat_states:
            with _cat_locks_mutex:
                if cat not in cat_states:   # double-checked locking
                    _init_cat(cat)

        # Acquires the cat's exclusive lock before processing.
        # Two packets from the same cat never process at the same time.
        with _get_cat_lock(cat):
            s = cat_states[cat]   # shortcut

            # ── SLEEP LOGIC ───────────────────────────────────────────────
            # If the bed sensor is active (cat sleeping), events from
            # other sensors are physically impossible. Any positive reading
            # from door/window/food is noise — discard silently.
            # Bed (04) and sandbox (05) are the only ones that always process.
            gato_dormindo = s["bed_occupied"]
            if gato_dormindo and sid in ("01", "02", "03"):
                # discard silently
                return

            # ── DOOR ──────────────────────────────────────────────────────
            if sid == "01":
                # Only acts on False→True transition (cat just went out)
                if is_new_event(cat, "door", cat_state):
                    if s["door_blocked"]:
                        # Door closed: notify attempt with throttle to avoid flooding
                        if _can_send_subtle(cat, "door"):
                            send_interface_alert({
                                "sensor": "door", "cat_name": cat,
                                "message": f"{cat} tried to leave, but the door is blocked.",
                                "subtle": True, "timestamp": datetime.now().isoformat(),
                            })
                    else:
                        s["door_count"] += 1
                        update_cat_stats(cat, "door")
                        resp = atuator_access_conn.call("door", {"count": s["door_count"], "cat_name": cat})
                        resp["sensor"]    = "door"
                        resp["cat_name"]  = cat
                        resp["estado"]    = "aventureiro"
                        resp["timestamp"] = resp.get("timestamp") or datetime.now().isoformat()
                        if not resp.get("message"):
                            resp["message"] = f"{cat} went out through the door. (exit {s['door_count']})"
                            resp["subtle"]  = True
                        send_interface_alert(resp)
                        if resp.get("action") == "block_door":
                            s["door_blocked"] = True
                            s["door_count"]   = 0

                _append_log(get_log_path("door_monitorator.json"), {
                    "cat_name": cat, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "cat_state": cat_state, "total_exits": s["door_count"],
                    "blocked": s["door_blocked"],
                })

            # ── WINDOW ────────────────────────────────────────────────────
            elif sid == "03":
                if is_new_event(cat, "window", cat_state):
                    if s["window_blocked"]:
                        if _can_send_subtle(cat, "window"):
                            send_interface_alert({
                                "sensor": "window", "cat_name": cat,
                                "message": f"{cat} tried to go out through the window, but it is blocked.",
                                "subtle": True, "timestamp": datetime.now().isoformat(),
                            })
                    else:
                        s["window_count"] += 1
                        update_cat_stats(cat, "window")
                        resp = atuator_access_conn.call("window", {"count": s["window_count"], "cat_name": cat})
                        resp["sensor"]    = "window"
                        resp["cat_name"]  = cat
                        resp["estado"]    = "aventureiro"
                        resp["timestamp"] = resp.get("timestamp") or datetime.now().isoformat()
                        if not resp.get("message"):
                            resp["message"] = f"{cat} went out through the window. (exit {s['window_count']})"
                            resp["subtle"]  = True
                        send_interface_alert(resp)
                        if resp.get("action") == "block_window":
                            s["window_blocked"] = True
                            s["window_count"]   = 0

                _append_log(get_log_path("window_monitorator.json"), {
                    "cat_name": cat, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "cat_state": cat_state, "total_exits": s["window_count"],
                    "blocked": s["window_blocked"],
                })

            # ── FOOD ──────────────────────────────────────────────────────
            elif sid == "02":
                if is_new_event(cat, "food", cat_state):
                    if s["food_blocked"]:
                        if _can_send_subtle(cat, "food"):
                            send_interface_alert({
                                "sensor": "food", "cat_name": cat,
                                "message": f"{cat} tried to eat, but the dispenser is blocked.",
                                "subtle": True, "timestamp": datetime.now().isoformat(),
                            })
                    else:
                        s["food_count"] += 1
                        update_cat_stats(cat, "food")
                        resp = atuator_access_conn.call("food", {"count": s["food_count"], "cat_name": cat})
                        resp["sensor"]    = "food"
                        resp["cat_name"]  = cat
                        resp["estado"]    = "gordo" if resp.get("action") == "block_dispenser" else "comendo"
                        resp["timestamp"] = resp.get("timestamp") or datetime.now().isoformat()
                        if not resp.get("message"):
                            resp["message"] = f"{cat} ate. (meal {s['food_count']})"
                            resp["subtle"]  = True
                        send_interface_alert(resp)
                        if resp.get("action") == "block_dispenser":
                            s["food_blocked"] = True
                            s["food_count"]   = 0

                _append_log(get_log_path("dispenser_monitorator.json"), {
                    "cat_name": cat, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "cat_state": cat_state, "total_meals": s["food_count"],
                    "blocked": s["food_blocked"],
                })

            # ── BED ───────────────────────────────────────────────────────
            elif sid == "04":
                # Capture the previous state BEFORE is_new_event modifies prev_bed.
                # This allows detecting both entry and exit transitions from the bed.
                prev_bed_was = s.get("prev_bed")

                if is_new_event(cat, "bed", cat_state):
                    s["bed_count"] += 1
                    update_cat_stats(cat, "bed")
                    resp = atuator_welfare_conn.call("bed", {"count": s["bed_count"], "cat_name": cat})
                    resp["sensor"]    = "bed"
                    resp["cat_name"]  = cat
                    resp["estado"]    = "dormindo"
                    resp["timestamp"] = resp.get("timestamp") or datetime.now().isoformat()
                    if not resp.get("message"):
                        resp["message"] = f"{cat} went to sleep. (nap {s['bed_count']})"
                        resp["subtle"]  = True
                    send_interface_alert(resp)
                    if resp.get("reset_count"):
                        s["bed_count"] = 0

                # False/None → True transition: cat arrived at the bed
                if cat_state and not prev_bed_was:
                    s["bed_occupied"] = True
                    send_interface_alert({
                        "type": "state_update", "sensor": "bed",
                        "cat_name": cat, "estado": "dormindo",
                        "message": f"{cat} lay down on the bed.",
                        "subtle": True,
                        "timestamp": datetime.now().isoformat(),
                    })

                # True → False transition: cat left the bed
                elif not cat_state and prev_bed_was:
                    s["bed_occupied"] = False
                    send_interface_alert({
                        "type": "state_update", "sensor": "bed",
                        "cat_name": cat, "estado": "acordado",
                        "message": f"{cat} got off the bed.",
                        "subtle": True,
                        "timestamp": datetime.now().isoformat(),
                    })

                _append_log(get_log_path("bed_monitorator.json"), {
                    "cat_name": cat, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "cat_state": cat_state, "total_naps": s["bed_count"],
                    "bed_occupied": s["bed_occupied"],
                })

            # ── SANDBOX ───────────────────────────────────────────────────
            elif sid == "05":
                if is_new_event(cat, "sandbox", cat_state):
                    s["sandbox_count"] += 1
                    update_cat_stats(cat, "sandbox")
                    resp = atuator_welfare_conn.call("sandbox", {"count": s["sandbox_count"], "cat_name": cat})
                    resp["sensor"]    = "sandbox"
                    resp["cat_name"]  = cat
                    resp["timestamp"] = resp.get("timestamp") or datetime.now().isoformat()
                    if not resp.get("message"):
                        resp["message"] = f"{cat} used the sandbox. (visit {s['sandbox_count']})"
                        resp["subtle"]  = True
                    send_interface_alert(resp)
                    if resp.get("reset_count"):
                        s["sandbox_count"] = 0

                _append_log(get_log_path("sandbox_monitorator.json"), {
                    "cat_name": cat, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "cat_state": cat_state, "total_usage": s["sandbox_count"],
                })

    except Exception as e:
        print(f"[ERROR] {e}")


if __name__ == "__main__":
    initialize_server()