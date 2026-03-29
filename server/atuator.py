"""
ATUADOR - Servidor TCP independente.

Responsabilidade: receber o contador atual de um evento e decidir
  - se só emite um aviso
  - se bloqueia o dispositivo
  - se pede reset do contador

O atuador NÃO filtra frequência de chamadas — isso é trabalho do server.
O atuador NÃO mantém estado de contador — isso é trabalho do server.
O atuador APENAS aplica as regras de negócio e retorna a ação.

Regras:
  PORTA / JANELA
    > 5  saídas → avisa que o gato está inquieto
    > 10 saídas → bloqueia saída + pede confirmação do dono na interface

  COMIDA
    > 4 refeições → avisa que o gato pode estar comendo demais
    > 8 refeições → bloqueia dispenser + pede confirmação do dono

  CAMA
    > 15 sonecas → avisa que o gato pode estar triste/depressivo
                   (cama não é bloqueável; reset_count=True para o server
                    zerar após o dono pressionar 'ok' na interface)

  CAIXINHA
    > 3 visitas → avisa sobre possível problema de saúde
                  (caixinha não é bloqueável; mesma lógica de reset)
"""

import socket
import json
import threading
from datetime import datetime

HOST         = "0.0.0.0"
PORT_ATUATOR = 1000


# ══════════════════════════════════════════════
# Funções de decisão (puras — sem estado interno)
# ══════════════════════════════════════════════

def door_atuator(count: int, cat_name: str) -> dict:
    """
    Porta: 5 → aviso | >10 → bloqueio
    Quando bloqueia, o server seta door_blocked=True e zera o contador.
    Enquanto bloqueada, o server só notifica tentativas (sem chamar aqui).
    """
    alert = _base("door", cat_name)

    if count > 10:
        alert["action"]      = "block_door"
        alert["message"]     = (
            f"🚨 {cat_name} saiu {count} vezes! Porta bloqueada por segurança. "
            f"Abra a porta na interface quando quiser liberar o acesso."
        )
        alert["needs_owner"] = True   # sinaliza que a interface deve exibir botão de ação

    elif count > 5:
        alert["message"] = (
            f"⚠️ {cat_name} já saiu {count} vezes hoje — acima do normal. "
            f"Pode estar inquieto ou procurando atenção."
        )

    return alert


def window_atuator(count: int, cat_name: str) -> dict:
    """Janela: mesma lógica da porta."""
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
    Comida: 4 → aviso | >8 → bloqueio
    Normal para gatos é comer até 4 vezes ao dia.
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


def bed_atuator(count: int, cat_name: str) -> dict:
    """
    Cama: >15 sonecas → avisa sobre possível tristeza/depressão.
    Cama não é bloqueável. reset_count=True pede ao server para
    zerar o contador depois que o dono pressionar 'ok' na interface.
    """
    alert = _base("bed", cat_name)

    if count > 15:
        alert["message"]     = (
            f"😿 {cat_name} deitou na cama {count} vezes! "
            f"Isso pode indicar tristeza ou depressão felina. "
            f"Que tal brincar um pouco com ele?"
        )
        alert["reset_count"] = True   # server zera após confirmação do dono
        alert["needs_owner"] = True   # interface exibe botão 'ok'

    return alert


def sandbox_atuator(count: int, cat_name: str) -> dict:
    """
    Caixinha: >3 visitas → avisa sobre possível problema de saúde.
    Caixinha não é bloqueável. Mesmo esquema de reset da cama.
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


# ══════════════════════════════════════════════
# Despacho
# ══════════════════════════════════════════════

DISPATCH = {
    "door":    lambda p: door_atuator(p["count"], p["cat_name"]),
    "window":  lambda p: window_atuator(p["count"], p["cat_name"]),
    "food":    lambda p: food_atuator(p["count"], p["cat_name"]),
    "bed":     lambda p: bed_atuator(p["count"], p["cat_name"]),
    "sandbox": lambda p: sandbox_atuator(p["count"], p["cat_name"]),
}


# ══════════════════════════════════════════════
# Servidor TCP
# ══════════════════════════════════════════════

def handle_client(conn: socket.socket, addr):
    print(f"[ATUADOR] Conexão de {addr}")
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
        print(f"[ATUADOR] Erro {addr}: {e}")
    finally:
        conn.close()
        print(f"[ATUADOR] Desconectado: {addr}")


def main():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, PORT_ATUATOR))
    srv.listen()
    print(f"[ATUADOR] Escutando em {HOST}:{PORT_ATUATOR}")
    while True:
        conn, addr = srv.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()


if __name__ == "__main__":
    main()