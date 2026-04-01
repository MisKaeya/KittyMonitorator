#for statistical purposes, asures that the door is open 5% of the time, and closed 95% of the time.
import random 
import os
#used for persistency of data 
import json
#used for creating a log file with the date and time of the events, and the state of the cat and the door.
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

# Bed state: True = sleeping, False = waken
open_bed = True
# Cat state: True = sleeping, False = waken
cat_state = False

#This function uses random.choices to simulate the bed being stepped on or not, with a higher probability 
#of not being stepped on, so that the "special" event of the cat going to a nap happens less
#frequently, and, in advance, the author can controll what to do with the information the system provides.
def checking_bed ():
    bed = [True, False]
    movement = random.choices(bed, weights=[0.001, 0.999],k=1)[0]
    if cats.get(get_cat_name(),{}).get("castrado")==True:
        movement = random.choices(bed, weights=[0.01, 0.99],k=1)[0]
    return movement
# Counter for the number of times the cat has gone outside through the window
bed_naps = 0

while open_bed:
    action = checking_bed()
    msg = "Sem peso detectado."    
    if action:
        msg = "peso detectado."        
        if not cat_state:
            cat_state = True
            bed_naps += 1
            
        else:
            cat_state = False
        
        packege ={
        "sensorID": '04',
        "cat_name": get_cat_name(),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "cat_state": cat_state,
        "bed_msg": msg,
        "total_naps": bed_naps

        }
        sensor_socket.sendto(json.dumps(packege).encode(), (HOST, PORT_SENSOR))
   
    print(msg) 
    # Requested time between each check, in seconds. Adjust as needed.
    time.sleep(0.001)