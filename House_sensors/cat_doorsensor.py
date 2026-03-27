import random
import time
import socket
from datetime import datetime
import json

HOST = "127.0.0.1"
PORT_SENSOR = 1001
door_sensor_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
CATS_FILE = os.path.join(os.path.dirname(__file__), "..", "interface", "cats.json")


def get_cat_name():
    try:
        with open(CATS_FILE, "r", encoding="utf-8") as f:
            cats = json.load(f)
            if cats:
                return random.choice(list(cats.keys()))
    except Exception:
        pass
    return ""

# Door state: True = open, False = closed
open_door = True
# Cat state: True = outside, False = inside
cat_state = False

#This function uses random.choices to simulate the door being open or closed, with a higher probability 
#of being closed (9.5) than open (0.5), so that the "special" event of the cat going outside happens less
#frequently, and, in advance, the author can controll what to do with the information the system provides.
def checking_door ():
    door = [True, False]
    movement = random.choices(door, weights=[5, 5],k=1)[0]
    
    return movement


#Loop that continuously checks the door state and updates the cat state accordingly. 
#It also logs the events to a JSON file and prints messages to the console. The loop 
#runs indefinitely until the open_door variable is set to False.
door_hangouts = 0

while open_door:
    action = checking_door()    
    msg = "Sem movimento detectado."    
    #Logic of definition of the cat state.
    if action:
        msg = "movimento detectado."        
        if not cat_state:
            cat_state = True
            door_hangouts += 1
        else:
            cat_state = False
    packege = {
        "sensorID": '01',
        "cat_name": get_cat_name(),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "cat_state": cat_state,
        "door_msg": msg,
        "door_hangouts": door_hangouts
    }
        
    door_sensor_socket.sendto(json.dumps(packege).encode(), (HOST, PORT_SENSOR))
   
    print(msg) 
    # Requested time between each check, in seconds. Adjust as needed.
    time.sleep(0.001)
