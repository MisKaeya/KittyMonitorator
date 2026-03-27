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

HOST = "127.0.0.1"
PORT_SENSOR = 1001
food_sensor_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# Dispencer state: True = open, False = closed
open_dispencer = True
# Cat state: True = comendo, False = inativo
cat_state = False
meals = 0
cat_dict = {}

#This function uses random.choices to simulate the door being open or closed, with a higher probability 
#of being closed (9.5) than open (0.5), so that the "special" event of the cat going outside happens less
#frequently, and, in advance, the author can controll what to do with the information the system provides.
def checking_dispencer ():
    dispencer = [True, False]
    movement = random.choices(dispencer, weights=[0.1,9.9],k=1)[0]
    
    return movement


#Loop that continuously checks the dispencer state and updates the cat state accordingly. 
#It also logs the events to a JSON file and prints messages to the console. The loop 
#runs indefinitely until the open_dispencer variable is set to False.
while open_dispencer:
    action = checking_dispencer()
    msg = "Sem movimento detectado."    
    #Logic of definition of the cat state.
    if action:
        msg = "movimento detectado."
                
        if not cat_state:
            cat_state = True
            meals += 1
        else:
            cat_state = False
        
             
    packege = {
        "sensorID": '02',
        "cat_name": "",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "cat_state": cat_state,
        "dispencer_msg": msg,
        "total_of_meals": meals
    }
    
    food_sensor_socket.sendto(json.dumps(packege).encode(), (HOST, PORT_SENSOR))
   
    print(msg) 
    # Requested time between each check, in seconds. Adjust as needed.
    time.sleep(0.001)
