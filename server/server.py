#for statistical purposes, asures that the door is open 5% of the time, and closed 95% of the time.
import random 
#used for persistency of data 
import json
#used for creating a log file with the date and time of the events, and the state of the cat and the door.
import os
#used for creating a log file with the date and time of the events, and the state of the cat and the door.
from datetime import datetime
import time
import socket
import threading

HOST = "127.0.0.1"
PORT_SERVER = 1004
PORT_APP = 1005
PORT_SENSOR = 1001
PORT_ATUATOR = 1000

def initialize_server():
    #initializes the atuator as an IPV4 TCP server, and listens for connections. When a connection is established, it starts a new thread to handle the client.
    atuator_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    atuator_socket.bind((HOST, PORT_ATUATOR))
    atuator_socket.listen()
     
    door_sensor_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    door_sensor_socket.bind((HOST, PORT_SENSOR))

    sensor_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sensor_socket.bind((HOST, PORT_SENSOR))

    food_sensor_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    food_sensor_socket.bind((HOST, PORT_SENSOR))

    interface_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    interface_socket.bind((HOST, PORT_APP))
    interface_socket.listen()


    print(f"Atuador iniciado em {HOST}:{PORT_ATUATOR}")
    while True:
        data = door_sensor_socket.recvfrom(1024)
        try:
            data = json.loads(data[0].decode('utf-8'))
            if  data["door_msg"]== "movimento detectado.":
                print(data)
                saving_door_data(data["cat_state"],data["door_msg"],data["door_hangouts"])
        except Exception as e:
            print(f"Erro ao processar os dados recebidos do sensor da porta: {e}")
        data_= sensor_socket.recvfrom(1024)
        try:
            data_ = json.loads(data_[0].decode('utf-8'))
            if  data_["window_msg"]== "movimento detectado.":
                print(data_)
                saving_window_data(data_["cat_state"],data_["window_msg"],data_["total_hangouts"])
        except Exception as e:
            print(f"Erro ao processar os dados recebidos do sensor da janela: {e}") 
        data__ = food_sensor_socket.recvfrom(1024)
        try:
            data__ = json.loads(data__[0].decode('utf-8'))
            if  data__["dispencer_msg"]== "O gatinho está comendo!":
                print(data__)
                saving_food_data(data__["cat_state"],data__["dispencer_msg"],data__["total_of_meals"])
        except Exception as e:
            print(f"Erro ao processar os dados recebidos do sensor do dispenser: {e}")

        client_socket, addr = atuator_socket.accept()
        print(f"Conexão estabelecida com {addr}")
        threading.Thread(target=initialize_server, args=(client_socket,)).start()
        
# Door state: True = open, False = closed


door_log = "door_monitorator.json"
def saving_door_data(cat_state,door_msg,door_hangouts):
    if cat_state:
        door_msg = "O gatinho saiu!"
    elif cat_state == False:
        door_msg = "O gatinho voltou para casa pela portinha!"
    register = {
        "cat_name": "",
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

window_log = "window_monitorator.json"
def saving_window_data(cat_state,window_msg,window_hangouts):
    
    if cat_state:
        window_msg = "O gatinho saiu!"        
    elif cat_state == False:
        window_msg = "O gatinho voltou para casa pela janela!"
    register = {
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

dispencer_log = "dispencer_monitorator.json"

cat_message = ["seu gatinho está batendo na máquina, socorro!",
                         "seu gatinho sentou diante do sensor em protesto, bloqueando a passagem. Por favor, retire-o desse local.",
                         "seu gatinho está miando sem parar, talvez um conversa ou uma brincadeira possa acalmá-lo",
                         "seu gatinho está em cima da máquina, gerando sobreaquecimento no motor. Por favor, retire-o desse local",
                         "talvez seu gatinho precise de uma consulta no veterinário",
                         "caramba, seu gato sente fome, hein?!"
                         "brincar com os pets pode ajudar a regular os níveis de ansiedade que induzem eles a comer"
                         "já pensou em comprar um novo brinquedo para seu gatinho?"]


def saving_food_data(cat_state,dispencer_msg,meals):
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

initialize_server()
