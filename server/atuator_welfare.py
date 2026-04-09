"""
WELFARE ATUATOR - TCP independent server.

Responsabilities: to monitor health and cat's beahvior.
  - Bed     : >15 naps → warns about likely kitty sadness/depression 
  - Sand box : >3 visits  → waarns about likely cat's health problem

These sensors DO NOT block the devices. Both of them use reset_count=True
so that the server set the counter to zero after the owner ratify at the interface.

Treated sensors: bed (04), sandbox (05)
TCP port: 2003
"""

import socket
import json
import threading
from datetime import datetime

HOST         = "0.0.0.0"
PORT_ATUATOR = 2003


# ---------------------------------------------
# Decision routines (pure — no internal state)
# ---------------------------------------------

def bed_atuator(count: int, cat_name: str) -> dict:
    """
    Bed     : >15 naps → warns about likely kitty sadness/depression
    The bed is not lockable. reset_count=True asks the server to set the
    counter to zero after the owner pess 'ok' at the interface.
    """
    alert = _base("bed", cat_name)

    if count > 15:
        alert["message"]     = (
            f"😿 {cat_name} deitou na cama {count} vezes! "
            f"Isso pode indicar tristeza ou depressão felina. "
            f"Que tal brincar um pouco com ele?"
        )
        alert["reset_count"] = True
        alert["needs_owner"] = True

    return alert


def sandbox_atuator(count: int, cat_name: str) -> dict:
    """
    Sand box : >3 visits  → waarns about likely cat's health problem
    The sendbox is not lockable.The same logic display from the bed routine.
    """
    alert = _base("sandbox", cat_name)

    if count > 3:
        alert["message"]     = (
            f"🏥 {cat_name} usou a caixinha {count} vezes! "
            f"Isso pode indicar incontinência urinária, diarreia ou outro "
            f"problema de saúde. Considere uma consulta veterinária."
        )
        alert["reset_count"] = True
        alert["needs_owner"] = True

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


# ---------------------------------------------
# Dispatch
# ---------------------------------------------

DISPATCH = {
    "bed":     lambda p: bed_atuator(p["count"], p["cat_name"]),
    "sandbox": lambda p: sandbox_atuator(p["count"], p["cat_name"]),
}


# ---------------------------------------------
# TCP server
# ---------------------------------------------

def handle_client(conn: socket.socket, addr):
    print(f"[ATUADOR-WELFARE] Conexão de {addr}")
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
        print(f"[ATUADOR-WELFARE] Erro {addr}: {e}")
    finally:
        conn.close()
        print(f"[ATUADOR-WELFARE] Desconectado: {addr}")


def main():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, PORT_ATUATOR))
    srv.listen()
    print(f"[ATUADOR-WELFARE] Escutando em {HOST}:{PORT_ATUATOR}")
    while True:
        conn, addr = srv.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()


if __name__ == "__main__":
    main()
