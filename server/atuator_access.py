"""
ACCESS ATUATOR - independent TCP server.

Responsabilities: controll access and feedig devices.
  - Door   : >5 hangouts → warning | >10 → block
  - Window  : >5 hangouts → warning | >10 → block
  - Food  : >4 meals → warning | >8 → block

Assisted sensors: door (01), window (03), food (02)
TCP port: 2000
"""

import socket
import json
import threading
from datetime import datetime

HOST         = "0.0.0.0"
PORT_ATUATOR = 2000


# ----------------------------------------------
# Decision functions (tottaly pure — no internal state)
# ----------------------------------------------

def door_atuator(count: int, cat_name: str) -> dict:
    """
    Door   : >5 hangouts → warning | >10 → block
    When blocked, the server sets door_blocked=True and throws the counter to 0.
    """
    alert = _base("door", cat_name)

    if count > 10:
        alert["action"]      = "block_door"
        alert["message"]     = (
            f"🚨 {cat_name} saiu {count} vezes! Porta bloqueada por segurança. "
            f"Abra a porta na interface quando quiser liberar o acesso."
        )
        alert["needs_owner"] = True

    elif count > 5:
        alert["message"] = (
            f"⚠️ {cat_name} já saiu {count} vezes hoje — acima do normal. "
            f"Pode estar inquieto ou procurando atenção."
        )

    return alert


def window_atuator(count: int, cat_name: str) -> dict:
    """Window:same door's logic."""
    alert = _base("window", cat_name)

    if count > 10:
        alert["action"]      = "block_window"
        alert["message"]     = (
            f"🚨 {cat_name} saiu pela janela {count} vezes! Janela bloqueada. "
            f"Abra a janela na interface quando quiser liberar o acesso."
        )
        alert["needs_owner"] = True

    elif count > 5:
        alert["message"] = (
            f"⚠️ {cat_name} saiu pela janela {count} vezes hoje — acima do normal. "
            f"Pode estar inquieto ou procurando atenção."
        )

    return alert


def food_atuator(count: int, cat_name: str) -> dict:
    """
    Food  : >4 meals → warning | >8 → block
    The espected amount of times for a cat to eat, per day, is 4 times
    """
    alert = _base("food", cat_name)

    if count > 8:
        alert["action"]      = "block_dispenser"
        alert["message"]     = (
            f"🚨 {cat_name} comeu {count} vezes! Dispenser bloqueado. "
            f"Isso pode indicar ansiedade alimentar. "
            f"Desbloqueie na interface quando quiser liberar."
        )
        alert["needs_owner"] = True

    elif count > 4:
        alert["message"] = (
            f"⚠️ {cat_name} já comeu {count} vezes hoje. "
            f"O ideal é até 4 refeições/dia — considere reajustar a dosagem do dispenser."
        )

    return alert


def _base(sensor: str, cat_name: str) -> dict:
    return {
        "sensor":      sensor,
        "cat_name":    cat_name,
        "timestamp":   datetime.now().isoformat(),
        "action":      None,
        "message":     None,
        "reset_count": False,
        "needs_owner": False,
    }


# ----------------------------------------------
# Dispatch
# ----------------------------------------------

DISPATCH = {
    "door":   lambda p: door_atuator(p["count"], p["cat_name"]),
    "window": lambda p: window_atuator(p["count"], p["cat_name"]),
    "food":   lambda p: food_atuator(p["count"], p["cat_name"]),
}


# ---------------------------------------------
# Server TCP
# ---------------------------------------------

def handle_client(conn: socket.socket, addr):
    print(f"[ATUADOR-ACESSO] Conexão de {addr}")
    buf = ""
    try:
        while True:
            chunk = conn.recv(4096)
            if not chunk:
                break
            buf += chunk.decode()
            while "\n" in buf:
                line, buf = buf.split("\n", 1)
                line = line.strip()
                if not line:
                    continue
                try:
                    req         = json.loads(line)
                    sensor_type = req.get("sensor_type")
                    params      = req.get("params", {})
                    response    = DISPATCH[sensor_type](params) if sensor_type in DISPATCH else {"error": f"Sensor desconhecido: {sensor_type}"}
                    conn.sendall((json.dumps(response, ensure_ascii=False) + "\n").encode())
                except json.JSONDecodeError as e:
                    conn.sendall((json.dumps({"error": str(e)}) + "\n").encode())
    except Exception as e:
        print(f"[ATUADOR-ACESSO] Erro {addr}: {e}")
    finally:
        conn.close()
        print(f"[ATUADOR-ACESSO] Desconectado: {addr}")


def main():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, PORT_ATUATOR))
    srv.listen()
    print(f"[ATUADOR-ACESSO] Escutando em {HOST}:{PORT_ATUATOR}")
    while True:
        conn, addr = srv.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()


if __name__ == "__main__":
    main()
