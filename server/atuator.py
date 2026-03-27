import House_sensors.cat_doorsensor
def door_atuator(door_state):
    if House_sensors.cat_doorsensor.door_hangouts >=5:
        door_state = True
        print("O gatinho já saiu 5 vezes pela porta, talvez seja melhor fechar a porta para evitar que ele saia mais vezes.")
    elif House_sensors.cat_doorsensor.door_hangouts >10:
        door_state = False
        print("O gatinho já saiu 10 vezes pela porta, fechamos a porta para evitar que ele saia mais vezes.")
    else:
        door_state = True
        print("O gatinho está muito parado, talvez sair para uma caminhada junto ao pet seja legal.")

import House_sensors.cat_windowsensor
def window_atuator(window_state):
    if House_sensors.cat_windowsensor.window_hangouts >=5:
        window_state = True
        print("O gatinho já saiu 5 vezes pela janela, talvez seja melhor fechar a janela para evitar que ele saia mais vezes.")
    elif House_sensors.cat_windowsensor.window_hangouts >10:
        window_state = False
        print("O gatinho já saiu 10 vezes pela janela, fechamos a janela para evitar que ele saia mais vezes.")
    else:
        window_state = True
        print("O gatinho está muito parado, talvez sair para uma caminhada junto ao pet seja legal.")

def food_atuator(meals):
    if meals > 5:
        open_dispenser = True
        print("O gatinho comeu demais! Ele precisa de uma pausa. Em breve o dispenser será desligado.")
    elif meals >=7:
        open_dispenser = False
        print("O gatinho comeu demais! Ele precisa de uma pausa. O dispenser foi desligado.")


def clean_box():
    if box_state == False:
        print('Caixa foi limpa')