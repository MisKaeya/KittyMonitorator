"""
SERVER PRINCIPAL

Responsabilidades:
  - Receber pacotes UDP dos sensores
  - Rastrear estado anterior de cada gato/sensor (para detectar mudança real de estado)
  - Chamar o atuador SOMENTE quando há mudança de estado (False→True)
  - Aplicar as ações retornadas pelo atuador (bloquear, resetar, alertar interface)
  - Encaminhar mensagens do atuador para a interface
"""

import random
import json
import os
import socket
import threading
from datetime import datetime

HOST         = "127.0.0.1"
PORT_APP     = 1005
PORT_SENSOR  = 1001
PORT_ATUATOR = 1000
ATUATOR_HOST = "127.0.0.1"

LOGS_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

CAT_JSON_FILE = os.path.join(os.path.dirname(__file__), "..", "interface", "cats.json")

interface_clients = []
clients_lock      = threading.Lock()
cat_stats         = {}
cat_states        = {}

# Tempo mínimo (segundos) para que dois eventos do mesmo sensor/gato
# sejam reconhecidos como eventos DISTINTOS.
# Resolve o problema do sensor alternando True/False a 0.001s:
# uma visita ao banheiro de 30s não vira 15000 contagens.
# Ajuste conforme a duração mínima realista de cada evento na simulação.
MIN_EVENT_INTERVAL = {
    "door":    2,    # uma saída dura pelo menos 2s
    "window":  2,
    "food":    5,    # uma refeição dura pelo menos 5s
    "bed":    10,    # uma soneca dura pelo menos 10s
    "sandbox": 10,   # uma visita ao banheiro dura pelo menos 10s
}


# ══════════════════════════════════════════════
# Comunicação com o Atuador
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
        print(f"[SERVER] Conectado ao atuador {self.host}:{self.port}")

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
                    print(f"[SERVER] Erro atuador (tentativa {attempt+1}): {e}")
                    try: self._sock.close()
                    except: pass
                    self._sock   = None
                    self._buffer = ""
            return {"action": None, "message": None, "reset_count": False}


atuator_conn = AtuatorConnection(ATUATOR_HOST, PORT_ATUATOR)


# ══════════════════════════════════════════════
# Estado por gato
# ══════════════════════════════════════════════

def _init_cat(cat_name: str):
    """
    Inicializa o estado de um gato.

    prev_*  → último cat_state recebido por sensor.
              O server só chama o atuador quando esse valor muda
              (False/None → True). Isso garante que cada evento
              físico seja contado uma única vez, independentemente
              de quantos pacotes UDP o sensor emite por segundo.

    *_count → contador de eventos do dia, resetado pelo atuador
              após ação crítica ou confirmação do dono na interface.

    *_blocked → flag de bloqueio. Quando True, o sensor continua
                detectando, mas o atuador só notifica tentativas.
    """
    cat_states[cat_name] = {
        # contadores
        "door_count":    0,
        "window_count":  0,
        "food_count":    0,
        "bed_count":     0,
        "sandbox_count": 0,

        # bloqueios (porta, janela e comida podem ser bloqueados)
        "door_blocked":    False,
        "window_blocked":  False,
        "food_blocked":    False,

        # estado anterior por sensor (controle de transição False→True)
        "prev_door":    None,
        "prev_window":  None,
        "prev_food":    None,
        "prev_bed":     None,
        "prev_sandbox": None,

        # timestamp do último evento CONTADO por sensor.
        # Impede que a alternância rápida True/False do sensor
        # (a cada 0.001s) gere múltiplas contagens para um mesmo
        # evento físico. Dois True consecutivos só viram dois
        # eventos distintos se o tempo entre eles for >= MIN_EVENT_INTERVAL.
        "last_event_door":    None,
        "last_event_window":  None,
        "last_event_food":    None,
        "last_event_bed":     None,
        "last_event_sandbox": None,
    }


def is_new_event(cat_name: str, sensor_key: str, current: bool) -> bool:
    """
    Retorna True apenas quando:
      1. O estado atual é True (sensor ativo)
      2. O estado anterior era False ou None (transição real)
      3. Passou tempo suficiente desde o último evento contado (MIN_EVENT_INTERVAL)

    As condições 1+2 sozinhas não bastam porque o sensor alterna
    True/False a cada 0.001s enquanto o evento está ativo — gerando
    centenas de "bordas de subida" por segundo para um único evento físico.
    A condição 3 garante que dois True separados por menos de N segundos
    sejam tratados como o mesmo evento, não como eventos distintos.
    """
    if not current:
        cat_states[cat_name][f"prev_{sensor_key}"] = current
        return False

    prev     = cat_states[cat_name].get(f"prev_{sensor_key}")
    last     = cat_states[cat_name].get(f"last_event_{sensor_key}")
    now      = datetime.now()
    interval = MIN_EVENT_INTERVAL.get(sensor_key, 2)

    cat_states[cat_name][f"prev_{sensor_key}"] = current

    # É novo evento se: nunca foi contado OU passou tempo suficiente
    if last is None or (now - last).total_seconds() >= interval:
        cat_states[cat_name][f"last_event_{sensor_key}"] = now
        return True

    return False


# ══════════════════════════════════════════════
# Interface
# ══════════════════════════════════════════════

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
    Processa comandos vindos da interface (app do dono).

    open_door / open_window / unblock_food:
      O dono decidiu reabrir o dispositivo. O server desbloqueia
      e zera o contador para que o ciclo recomece do zero.

    ok_bed / ok_sandbox:
      O dono confirmou ('ok') o aviso da cama/caixinha.
      O server apenas zera o contador.
    """
    command = cmd.get("command")
    cat     = cmd.get("cat")
    if cat not in cat_states:
        return

    if command == "open_door":
        cat_states[cat]["door_blocked"] = False
        cat_states[cat]["door_count"]   = 0
        send_interface_alert({"message": f"Porta reaberta para {cat}.", "subtle": False, "timestamp": datetime.now().isoformat()})

    elif command == "open_window":
        cat_states[cat]["window_blocked"] = False
        cat_states[cat]["window_count"]   = 0
        send_interface_alert({"message": f"Janela reaberta para {cat}.", "subtle": False, "timestamp": datetime.now().isoformat()})

    elif command == "unblock_food":
        cat_states[cat]["food_blocked"] = False
        cat_states[cat]["food_count"]   = 0
        send_interface_alert({"message": f"Dispenser reaberto para {cat}.", "subtle": False, "timestamp": datetime.now().isoformat()})

    elif command == "close_door":
        cat_states[cat]["door_blocked"] = True
        send_interface_alert({"message": f"Porta fechada manualmente para {cat}.", "subtle": True, "timestamp": datetime.now().isoformat()})

    elif command == "close_window":
        cat_states[cat]["window_blocked"] = True
        send_interface_alert({"message": f"Janela fechada manualmente para {cat}.", "subtle": True, "timestamp": datetime.now().isoformat()})

    elif command == "block_food":
        cat_states[cat]["food_blocked"] = True
        send_interface_alert({"message": f"Dispenser bloqueado manualmente para {cat}.", "subtle": True, "timestamp": datetime.now().isoformat()})

    elif command in ("ok_bed", "ok_sandbox"):
        sensor = command.replace("ok_", "")
        cat_states[cat][f"{sensor}_count"] = 0
        send_interface_alert({"message": f"Contador de {sensor} zerado para {cat}.", "subtle": True, "timestamp": datetime.now().isoformat()})


def handle_interface_client(conn, addr):
    print(f"[SERVER] Interface conectada: {addr}")
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
        print(f"[SERVER] Erro interface: {e}")
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
    dados = []
    if os.path.exists(path):
        with open(path) as f:
            try: dados = json.load(f)
            except: dados = []
    dados.append(record)
    with open(path, "w") as f:
        json.dump(dados, f, indent=4)

def update_cat_stats(cat_name, sensor_type):
    if cat_name not in cat_stats:
        cat_stats[cat_name] = {"door": 0, "window": 0, "food": 0, "sandbox": 0, "bed": 0}
    if sensor_type in cat_stats[cat_name]:
        cat_stats[cat_name][sensor_type] += 1
    try:
        with open(get_log_path("cat_activity.json"), "w", encoding="utf-8") as f:
            json.dump(cat_stats, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Erro stats: {e}")


# ══════════════════════════════════════════════
# Loop principal
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

    print(f"[SERVER] UDP sensores  → {HOST}:{PORT_SENSOR}")
    print(f"[SERVER] TCP interface → {HOST}:{PORT_APP}")
    print(f"[SERVER] TCP atuador   → {ATUATOR_HOST}:{PORT_ATUATOR}")

    while True:
        packet, _ = sensor_sock.recvfrom(2048)
        try:
            data      = json.loads(packet.decode())
            sid       = data.get("sensorID")
            cat       = data.get("cat_name", "desconhecido")
            cat_state = data.get("cat_state")

            if cat not in cat_states:
                _init_cat(cat)

            s = cat_states[cat]   # atalho

            # ── PORTA ────────────────────────────────────────────────────
            if sid == "01":
                # Só age na transição False→True (o gato acabou de sair)
                if is_new_event(cat, "door", cat_state):
                    if s["door_blocked"]:
                        # Porta fechada: só notifica tentativa, não incrementa
                        send_interface_alert({
                            "sensor": "door", "cat_name": cat,
                            "message": f"{cat} tentou sair, mas a porta está bloqueada.",
                            "subtle": True, "timestamp": datetime.now().isoformat(),
                        })
                    else:
                        s["door_count"] += 1
                        update_cat_stats(cat, "door")
                        resp = atuator_conn.call("door", {"count": s["door_count"], "cat_name": cat})

                        if resp.get("message"):
                            send_interface_alert(resp)

                        if resp.get("action") == "block_door":
                            s["door_blocked"] = True
                            s["door_count"]   = 0   # reseta ao bloquear

                _append_log(get_log_path("door_monitorator.json"), {
                    "cat_name": cat, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "cat_state": cat_state, "total_exits": s["door_count"],
                    "blocked": s["door_blocked"],
                })

            # ── JANELA ───────────────────────────────────────────────────
            elif sid == "03":
                if is_new_event(cat, "window", cat_state):
                    if s["window_blocked"]:
                        send_interface_alert({
                            "sensor": "window", "cat_name": cat,
                            "message": f"{cat} tentou sair pela janela, mas está bloqueada.",
                            "subtle": True, "timestamp": datetime.now().isoformat(),
                        })
                    else:
                        s["window_count"] += 1
                        update_cat_stats(cat, "window")
                        resp = atuator_conn.call("window", {"count": s["window_count"], "cat_name": cat})

                        if resp.get("message"):
                            send_interface_alert(resp)

                        if resp.get("action") == "block_window":
                            s["window_blocked"] = True
                            s["window_count"]   = 0

                _append_log(get_log_path("window_monitorator.json"), {
                    "cat_name": cat, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "cat_state": cat_state, "total_exits": s["window_count"],
                    "blocked": s["window_blocked"],
                })

            # ── COMIDA ───────────────────────────────────────────────────
            elif sid == "02":
                if is_new_event(cat, "food", cat_state):
                    if s["food_blocked"]:
                        send_interface_alert({
                            "sensor": "food", "cat_name": cat,
                            "message": f"{cat} tentou comer, mas o dispenser está bloqueado.",
                            "subtle": True, "timestamp": datetime.now().isoformat(),
                        })
                    else:
                        s["food_count"] += 1
                        update_cat_stats(cat, "food")
                        resp = atuator_conn.call("food", {"count": s["food_count"], "cat_name": cat})

                        if resp.get("message"):
                            send_interface_alert(resp)

                        if resp.get("action") == "block_dispenser":
                            s["food_blocked"] = True
                            s["food_count"]   = 0

                _append_log(get_log_path("dispenser_monitorator.json"), {
                    "cat_name": cat, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "cat_state": cat_state, "total_meals": s["food_count"],
                    "blocked": s["food_blocked"],
                })

            # ── CAMA ─────────────────────────────────────────────────────
            elif sid == "04":
                # Cada True é uma soneca (o sensor já alterna True/False)
                if is_new_event(cat, "bed", cat_state):
                    s["bed_count"] += 1
                    update_cat_stats(cat, "bed")
                    resp = atuator_conn.call("bed", {"count": s["bed_count"], "cat_name": cat})

                    if resp.get("message"):
                        send_interface_alert(resp)

                    # Após aviso confirmado pelo dono (ok_bed), o contador
                    # é zerado pelo handle_command. O atuador sinaliza com
                    # reset_count=True para que o server saiba que deve aguardar.
                    if resp.get("reset_count"):
                        s["bed_count"] = 0

                _append_log(get_log_path("bed_monitorator.json"), {
                    "cat_name": cat, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "cat_state": cat_state, "total_naps": s["bed_count"],
                })

            # ── CAIXINHA ─────────────────────────────────────────────────
            elif sid == "05":
                if is_new_event(cat, "sandbox", cat_state):
                    s["sandbox_count"] += 1
                    update_cat_stats(cat, "sandbox")
                    resp = atuator_conn.call("sandbox", {"count": s["sandbox_count"], "cat_name": cat})

                    if resp.get("message"):
                        send_interface_alert(resp)

                    if resp.get("reset_count"):
                        s["sandbox_count"] = 0

                _append_log(get_log_path("sandbox_monitorator.json"), {
                    "cat_name": cat, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "cat_state": cat_state, "total_usage": s["sandbox_count"],
                })

        except Exception as e:
            print(f"[ERRO] {e}")


if __name__ == "__main__":
    initialize_server()