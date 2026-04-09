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

HOST = os.environ.get("SERVER_HOST", "kitty_server")
PORT_SENSOR = 2001 
sensor_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
CATS_FILE = os.path.join(os.path.dirname(__file__), "..", "interface", "cats.json")
# Load cats data from the JSON file
with open(CATS_FILE, "r", encoding="utf-8") as f:
            cats = json.load(f)

def get_cat_name():
  #Loads cat data from the JSON file and puts the names of the cats in a list, then randomly selects one of the names and returns it. 
  # If there are no cats in the file, it returns an empty string.
    try:
        with open(CATS_FILE, "r", encoding="utf-8") as f:
            cats = json.load(f)
            if cats:
                return random.choice(list(cats.keys()))
    except Exception:
        pass
    return ""

    
# Window state: True = open, False = closed
open_window = True
# Cat state: True = outside, False = inside
cat_state = False

#This function uses random.choices to simulate the window being open or closed, with a higher probability 
#of being closed (9.5) than open (0.5), so that the "special" event of the cat going outside happens less
#frequently, and, in advance, the author can controll what to do with the information the system provides.
def checking_window ():
    
    window = [True, False]
    movement = random.choices(window, weights=[0.0005, 0.9995],k=1)[0]
    if cats.get(get_cat_name(),{}).get("castrado")==True:
        movement = random.choices(window, weights=[0.0001, 0.9999],k=1)[0]
    
    return movement
# Counter for the number of times the cat has gone outside through the window
window_hangouts = 0

#The heart of the sensor, this is where the informations are created and sent to the server, the sensor checks if the window is open, 
# if it is, it checks if there is movement, if there is movement, it changes the state of the cat and increments the counter of hangouts, 
# then it creates a package with all the information and sends it to the server.
while open_window:
    action = checking_window()
    msg = "Sem movimento detectado."    
    if action:
        msg = "movimento detectado."        
        if not cat_state:
            cat_state = True
            window_hangouts += 1
            
        else:
            cat_state = False
        
        packege ={
        "sensorID": '03',
        "cat_name": get_cat_name(),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "cat_state": cat_state,
        "window_msg": msg,
        "total_hangouts": window_hangouts

        }
        sensor_socket.sendto(json.dumps(packege).encode(), (HOST, PORT_SENSOR))
   
    print(msg) 
    # Requested time between each check, in seconds. Adjust as needed.
    time.sleep(0.1)
