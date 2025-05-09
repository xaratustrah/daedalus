#!/usr/bin/env python
"""
Daedalus MCU simulator

Jan 2025 xaratustrah@github

"""

import zmq
import json
import random
import time

SLEEP = 0.5

# publisher setup
context = zmq.Context()
socket = context.socket(zmq.PUB)
socket.bind("tcp://*:5556")

while True:

    xpos = {
        "name": "position",
        "ch": "x",
        "dev": "nozzle",
        "ldev": "daedalus",
        "raw": random.randint(0, 2**12 - 1),
        "value": round(random.uniform(0, 25), 2),
        "epoch_time": time.time(),
    }

    ypos = {
        "name": "position",
        "ch": "y",
        "dev": "nozzle",
        "ldev": "daedalus",
        "raw": random.randint(0, 2**12 - 1),
        "value": round(random.uniform(0, 25), 2),
        "epoch_time": time.time(),
    }

    zpos = {
        "name": "position",
        "ch": "z",
        "dev": "nozzle",
        "ldev": "daedalus",
        "raw": random.randint(0, 2**12 - 1),
        "value": round(random.uniform(0, 25), 2),
        "epoch_time": time.time(),
    }

    nozzle_pressure = {
        "name": "pressure",
        "ch": "0",
        "dev": "nozzle",
        "ldev": "daedalus",
        "raw": random.randint(0, 2**12 - 1),
        "value": round(random.uniform(0, 10), 2),
        "epoch_time": time.time(),
    }

    shutter_signal = {
        "name": "shutter",
        "ch": "0",
        "dev": "nozzle",
        "ldev": "daedalus",
        "type": "signal",
        "value": random.choice([True, False]),
        "epoch_time": time.time(),
    }

    shutter_sensor = {
        "name": "shutter",
        "ch": "0",
        "dev": "nozzle",
        "ldev": "daedalus",
        "type": "sensor",
        "value": random.choice([True, False]),
        "epoch_time": time.time(),
    }

    # s4 = {
    #     "name": "vacuum",
    #     "ch": 7,
    #     "dev": "GJ_S4",
    #     "ldev": "gj_maxigauge",
    #     "value": round(random.uniform(5e-10, 1e-4), 8),
    #     "epoch_time": time.time(),
    # }
    
    # e4 = {
    #     "name": "vacuum",
    #     "ch": 8,
    #     "dev": "GJ_E4",
    #     "ldev": "gj_maxigauge",
    #     "value": round(random.uniform(5e-10, 1e-4), 8),
    #     "epoch_time": time.time(),
    # }

    allofthem = {
        "xpos": xpos,
        "ypos": ypos,
        "zpos": zpos,
        "nozzle_pressure": nozzle_pressure,
        "shutter_signal": shutter_signal,
        "shutter_sensor": shutter_sensor,
#        "s4": s4,
#        "e4": e4,
    }

    message = json.dumps(allofthem)
    socket.send_string(message)
    print("\n", message)
    time.sleep(SLEEP)  # Adjust sleep time as needed
