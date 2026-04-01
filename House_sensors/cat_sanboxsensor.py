#for statistical purposes, asures that the door is open 5% of the time, and closed 95% of the time.
import random 
#used for persistency of data 
import json
#used for creating a log file with the date and time of the events, and the state of the cat and the door.
import os
from datetime import datetime
import time
#used for communication between the sensor and the server
import socket

HOST = "127.0.0.1"
PORT_SENSOR = 1001 
sensor_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
CATS_FILE = os.path.join(os.path.dirname(__file__), "..", "interface", "cats.json")

with open(CATS_FILE, "r", encoding="utf-8") as f:
            cats = json.load(f)

def get_cat_name():
    try:
        with open(CATS_FILE, "r", encoding="utf-8") as f:
            cats = json.load(f)
            if cats:
                return random.choice(list(cats.keys()))
    except Exception:
        pass
    return ""

# Window state: True = clean box, False = completely dirty box
box_state = True
# Cat state: True = using the box, False = not using the box
cat_state = False

#This function uses random.choices to simulate the window being open or closed, with a higher probability 
#of being closed (9.5) than open (0.5), so that the "special" event of the cat going outside happens less
#frequently, and, in advance, the author can controll what to do with the information the system provides.
def checking_box ():
    box_state = [True, False]
    movement = random.choices(box_state, weights=[0.001, 0.999],k=1)[0]
    if cats.get(get_cat_name(),{}).get("filhote")==True:
        movement = random.choices(box_state, weights=[0.01, 0.99],k=1)[0]
        
    return movement
# Counter for the number of times the cat has gone pooping or peeing in the box
sandbox_usage = 0

while box_state:
    action = checking_box()
    msg = "Sem movimento detectado."    
    if action:
        msg = "movimento detectado."        
        if not cat_state:
            cat_state = True
            sandbox_usage += 1
            
        else:
            cat_state = False
        
        packege ={
        "sensorID": '05',
        "cat_name": get_cat_name(),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "cat_state": cat_state,
        "sandbox_msg": msg,
        "total_usage": sandbox_usage

        }
        sensor_socket.sendto(json.dumps(packege).encode(), (HOST, PORT_SENSOR))
   
    print(msg) 
    # Requested time between each check, in seconds. Adjust as needed.
    time.sleep(0.001)
