import random 
import json
import os
from datetime import datetime, timedelta
import time
import socket
import threading
from atuator import door_atuator, window_atuator, food_atuator, sandbox_atuator, bed_atuator

HOST = "127.0.0.1"
PORT_SERVER = 1004
PORT_APP = 1005
PORT_SENSOR = 1001
PORT_ATUATOR = 1000

# Criar diretório para logs se não existir
LOGS_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

# Estado global de notificação do atuador
interface_clients = []
clients_lock = threading.Lock()

# Histórico de eventos sandbox para a janela de 1 hora
sandbox_history = []

# Estado de presença na cama (requerido para detecção de 20h simulada)
bed_presence_start = None

# Cat registry e estatísticas
CAT_JSON_FILE = os.path.join(os.path.dirname(__file__), "..", "interface", "cats.json")
cat_stats = {}
cat_states = {}


def load_cat_registry():
    try:
        with open(CAT_JSON_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def update_cat_stats(cat_name, sensor_type):
    if not cat_name:
        return
    if cat_name not in cat_stats:
        cat_stats[cat_name] = {
            "door": 0,
            "window": 0,
            "food": 0,
            "sandbox": 0,
            "bed": 0,
        }
    if sensor_type in cat_stats[cat_name]:
        cat_stats[cat_name][sensor_type] += 1
    cat_stats_path = get_log_path("cat_activity.json")
    try:
        with open(cat_stats_path, "w", encoding="utf-8") as f:
            json.dump(cat_stats, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Erro salvando estatísticas de gatos: {e}")


def handle_command(cmd):
    global cat_states
    if cmd.get("command") == "unblock_food":
        cat = cmd.get("cat")
        if cat in cat_states:
            cat_states[cat]["food_blocked"] = False
            cat_states[cat]["food_meals"] = 0
            alert = {"message": f"Dispenser desbloqueado para {cat}. Contador zerado.", "subtle": False, "timestamp": datetime.now().isoformat()}
            send_interface_alert(alert)
    elif cmd.get("command") == "open_door":
        cat = cmd.get("cat")
        if cat in cat_states:
            cat_states[cat]["door_closed"] = False
            cat_states[cat]["door_exits"] = 0
            alert = {"message": f"Porta aberta para {cat}. Contador zerado.", "subtle": False, "timestamp": datetime.now().isoformat()}
            send_interface_alert(alert)
    elif cmd.get("command") == "open_window":
        cat = cmd.get("cat")
        if cat in cat_states:
            cat_states[cat]["window_closed"] = False
            cat_states[cat]["window_exits"] = 0
            alert = {"message": f"Janela aberta para {cat}. Contador zerado.", "subtle": False, "timestamp": datetime.now().isoformat()}
            send_interface_alert(alert)


def get_log_path(filename):
    """Retorna o caminho completo para o arquivo de log"""
    return os.path.join(LOGS_DIR, filename)

def send_interface_alert(alert: dict):
    """Envia alerta JSON para todas conexões de interface ativas."""
    with clients_lock:
        closed = []
        for conn in interface_clients:
            try:
                payload = json.dumps(alert, ensure_ascii=False).encode('utf-8') + b"\n"
                conn.sendall(payload)
            except Exception:
                closed.append(conn)
        for conn in closed:
            try:
                conn.close()
            except Exception:
                pass
            interface_clients.remove(conn)


def handle_interface_client(conn, addr):
    print(f"Interface conectada: {addr}")
    with clients_lock:
        interface_clients.append(conn)

    try:
        buffer = ""
        while True:
            data = conn.recv(1024)
            if not data:
                break
            buffer += data.decode('utf-8')
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                try:
                    cmd = json.loads(line)
                    handle_command(cmd)
                except json.JSONDecodeError:
                    pass
    except Exception as e:
        print(f"Erro na conexão com interface: {e}")
    finally:
        with clients_lock:
            if conn in interface_clients:
                interface_clients.remove(conn)
        try:
            conn.close()
        except Exception:
            pass


def accept_interface_clients(interface_socket):
    while True:
        conn, addr = interface_socket.accept()
        threading.Thread(target=handle_interface_client, args=(conn, addr), daemon=True).start()


def initialize_server():
    #initializes the atuator as an IPV4 TCP server, and listens for connections. When a connection is established, it starts a new thread to handle the client.
    atuator_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    atuator_socket.bind((HOST, PORT_ATUATOR))
    atuator_socket.listen()    


    sensor_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sensor_socket.bind((HOST, PORT_SENSOR))


    interface_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    interface_socket.bind((HOST, PORT_APP))
    interface_socket.listen()

    threading.Thread(target=accept_interface_clients, args=(interface_socket,), daemon=True).start()

    print(f"Atuador iniciado em {HOST}:{PORT_ATUATOR}")
    print(f"Logs serão salvos em: {LOGS_DIR}")
    packet_count = 0
    while True:
        data_packet, addr = sensor_socket.recvfrom(1024)
        packet_count += 1
        try:
            data = json.loads(data_packet.decode('utf-8'))
            sensor_id = data.get("sensorID")
            cat_name = data.get("cat_name", "desconhecido")
            cat_registry = load_cat_registry()
            if cat_name and cat_name not in cat_registry:
                print(f"Aviso: gatinho '{cat_name}' não está no registro da interface (cats.json)")

            if cat_name not in cat_states:
                cat_states[cat_name] = {"door_exits": 0, "door_closed": False, "window_exits": 0, "window_closed": False, "food_meals": 0, "food_blocked": False, "sandbox_usage": 0, "bed_naps": 0}


            # Log a cada 100 pacotes recebidos
            if packet_count % 100 == 0:
                print(f"[INFO] {packet_count} pacotes recebidos até agora...")

            # Sensor 01: Door
            if sensor_id == '01':
                if data.get("cat_state"):  # exit
                    if not cat_states[cat_name]["door_closed"]:
                        cat_states[cat_name]["door_exits"] += 1
                        update_cat_stats(cat_name, "door")
                        alert = door_atuator(cat_states[cat_name]["door_exits"], cat_name)
                        if alert.get("action") == "close_door":
                            cat_states[cat_name]["door_closed"] = True
                    else:
                        alert = {"sensor": "door", "cat_name": cat_name, "message": f"{cat_name} tentou sair pela porta.", "subtle": True, "timestamp": datetime.now().isoformat()}
                else:
                    alert = None
                if alert:
                    send_interface_alert(alert)
                saving_door_data(data.get("cat_state"), data.get("door_msg"), cat_states[cat_name]["door_exits"], cat_name)

            # Sensor 02: Food/Dispenser
            elif sensor_id == '02':
                if data.get("cat_state"):  # eating
                    if not cat_states[cat_name]["food_blocked"]:
                        cat_states[cat_name]["food_meals"] += 1
                        update_cat_stats(cat_name, "food")
                        alert = food_atuator(cat_states[cat_name]["food_meals"], cat_name)
                        if alert.get("action") == "block_dispenser":
                            cat_states[cat_name]["food_blocked"] = True
                    else:
                        alert = {"sensor": "food", "cat_name": cat_name, "message": f"{cat_name} tentou comer.", "subtle": True, "timestamp": datetime.now().isoformat()}
                else:
                    alert = None
                if alert:
                    send_interface_alert(alert)
                saving_food_data(data.get("cat_state"), data.get("dispencer_msg"), cat_states[cat_name]["food_meals"], cat_name)

            # Sensor 03: Window
            elif sensor_id == '03':
                if data.get("cat_state"):  # exit
                    if not cat_states[cat_name]["window_closed"]:
                        cat_states[cat_name]["window_exits"] += 1
                        update_cat_stats(cat_name, "window")
                        alert = window_atuator(cat_states[cat_name]["window_exits"], cat_name)
                        if alert.get("action") == "close_window":
                            cat_states[cat_name]["window_closed"] = True
                    else:
                        alert = {"sensor": "window", "cat_name": cat_name, "message": f"{cat_name} tentou sair pela janela.", "subtle": True, "timestamp": datetime.now().isoformat()}
                else:
                    alert = None
                if alert:
                    send_interface_alert(alert)
                saving_window_data(data.get("cat_state"), data.get("window_msg"), cat_states[cat_name]["window_exits"], cat_name)

            # Sensor 04: Bed
            elif sensor_id == '04':
                cat_states[cat_name]["bed_naps"] += 1
                update_cat_stats(cat_name, "bed")
                alert = bed_atuator(data.get("cat_state"), cat_name)
                if alert.get("message") or alert.get("action"):
                    send_interface_alert(alert)
                saving_bed_data(data.get("cat_state"), data.get("bed_msg"), cat_states[cat_name]["bed_naps"], cat_name)

            # Sensor 05: Sandbox
            elif sensor_id == '05':
                cat_states[cat_name]["sandbox_usage"] += 1
                update_cat_stats(cat_name, "sandbox")
                sandbox_history.append(datetime.now())
                alert = sandbox_atuator(cat_states[cat_name]["sandbox_usage"], cat_name, sandbox_history)
                if alert.get("message") or alert.get("action"):
                    send_interface_alert(alert)
                saving_sandbox_data(data.get("cat_state"), data.get("sandbox_msg"), cat_states[cat_name]["sandbox_usage"], cat_name)

        except Exception as e:
            print(f"[ERRO] Ao processar os dados: {e}")
        
door_log = get_log_path("door_monitorator.json")
def saving_door_data(cat_state,door_msg,door_hangouts,cat_name="desconhecido"):
    if cat_state:
        door_msg = "O gatinho saiu!"
    elif cat_state == False:
        door_msg = "O gatinho voltou para casa pela portinha!"
    register = {
        "cat_name": cat_name,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "cat_state": cat_state,
        "door_msg": door_msg,
        "total_hangouts":door_hangouts
    }
    if os.path.exists(door_log):
            #opening with mode 'r' for saving the data in a list, a kind of history
            with open(door_log, "r") as f:
                try:
                    dados = json.load(f)
                except json.JSONDecodeError:
                    dados = []
        # Adding a new register to the list
            dados.append(register)

            # Saving back into the archive, without looding data 
            with open(door_log, "w") as f:
                json.dump(dados, f, indent=4)
    else:
        dados = []

        # Adding a new register to the list
        dados.append(register)

        # Saving back into the archive 
        with open(door_log, "w") as f:
            json.dump(dados, f, indent=4)

window_log = get_log_path("window_monitorator.json")
def saving_window_data(cat_state,window_msg,window_hangouts,cat_name="desconhecido"):
    
    if cat_state:
        window_msg = "O gatinho saiu!"        
    elif cat_state == False:
        window_msg = "O gatinho voltou para casa pela janela!"
    register = {
        "cat_name": cat_name,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "cat_state": cat_state,
        "window_msg": window_msg,
        "total_hangouts": window_hangouts
    }
    if os.path.exists(window_log):
            #opening with mode 'r' for saving the data in a list, a kind of history
            with open(window_log, "r") as f:
                try:
                    dados = json.load(f)
                except json.JSONDecodeError:
                    dados = []
        # Adding a new register to the list
            dados.append(register)

            # Saving back into the archive, without looding data 
            with open(window_log, "w") as f:
                json.dump(dados, f, indent=4)
    else:
        dados = []

        # Adding a new register to the list
        dados.append(register)

        # Saving back into the archive 
        with open(window_log, "w") as f:
            json.dump(dados, f, indent=4)

dispencer_log = get_log_path("dispencer_monitorator.json")

cat_message = ["seu gatinho está batendo na máquina, socorro!",
                         "seu gatinho sentou diante do sensor em protesto, bloqueando a passagem. Por favor, retire-o desse local.",
                         "seu gatinho está miando sem parar, talvez um conversa ou uma brincadeira possa acalmá-lo",
                         "seu gatinho está em cima da máquina, gerando sobreaquecimento no motor. Por favor, retire-o desse local",
                         "talvez seu gatinho precise de uma consulta no veterinário",
                         "caramba, seu gato sente fome, hein?!"
                         "brincar com os pets pode ajudar a regular os níveis de ansiedade que induzem eles a comer"
                         "já pensou em comprar um novo brinquedo para seu gatinho?"]


def saving_food_data(cat_state,dispencer_msg,meals,cat_name="desconhecido"):
    if meals > 7:
        dispencer_msg = random.choice(cat_message)
        meals = 8
    else:
        if cat_state:
            dispencer_msg = "O gatinho está comendo!"        
            if meals > 5:
                dispencer_msg = "O gatinho comeu demais! Ele precisa de uma pausa. Em breve o dispenser será desligado."

        elif cat_state == False:
            dispencer_msg = "O gatinho parou de comer."

         
    
    register = {
        "cat_name": cat_name,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "cat_state": cat_state,
        "dispencer_msg": dispencer_msg,
        "total_of_meals": meals
    }
    if os.path.exists(dispencer_log):
            #opening with mode 'r' for saving the data in a list, a kind of history
            with open(dispencer_log, "r") as f:
                try:
                    dados = json.load(f)
                except json.JSONDecodeError:
                    dados = []
        # Adding a new register to the list
            dados.append(register)

            # Saving back into the archive, without looding data 
            with open(dispencer_log, "w") as f:
                json.dump(dados, f, indent=4)
    else:
        dados = []

        # Adding a new register to the list
        dados.append(register)

        # Saving back into the archive 
        with open(dispencer_log, "w") as f:
            json.dump(dados, f, indent=4)

saving_bed_data_log = get_log_path("bed_monitorator.json")
def saving_bed_data(cat_state,bed_msg,total_naps,cat_name="desconhecido"):
    register = {
        "cat_name": cat_name,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "cat_state": cat_state,
        "bed_msg": bed_msg,
        "total_naps": total_naps
    }
    if os.path.exists(saving_bed_data_log):
            #opening with mode 'r' for saving the data in a list, a kind of history
            with open(saving_bed_data_log, "r") as f:
                try:
                    dados = json.load(f)
                except json.JSONDecodeError:
                    dados = []
        # Adding a new register to the list
            dados.append(register)

            # Saving back into the archive, without looding data 
            with open(saving_bed_data_log, "w") as f:
                json.dump(dados, f, indent=4)
    else:
        dados = []

        # Adding a new register to the list
        dados.append(register)

        # Saving back into the archive 
        with open(saving_bed_data_log, "w") as f:
            json.dump(dados, f, indent=4)
saving_sandbox_data_log = get_log_path("sandbox_monitorator.json")
def saving_sandbox_data(cat_state,sandbox_msg,total_usage,cat_name="desconhecido"):
    register = {
        "cat_name": cat_name,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "cat_state": cat_state,
        "sandbox_msg": sandbox_msg,
        "total_usage": total_usage
    }
    if os.path.exists(saving_sandbox_data_log):
            #opening with mode 'r' for saving the data in a list, a kind of history
            with open(saving_sandbox_data_log, "r") as f:
                try:
                    dados = json.load(f)
                except json.JSONDecodeError:
                    dados = []
        # Adding a new register to the list
            dados.append(register)

            # Saving back into the archive, without looding data 
            with open(saving_sandbox_data_log, "w") as f:
                json.dump(dados, f, indent=4)
    else:
        dados = []

        # Adding a new register to the list
        dados.append(register)

        # Saving back into the archive 
        with open(saving_sandbox_data_log, "w") as f:
            json.dump(dados, f, indent=4)

initialize_server()
