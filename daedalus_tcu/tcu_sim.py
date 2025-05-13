#!/usr/bin/env python
"""
Daedalus TCU simulator

Jan 2025 xaratustrah@github

"""

import zmq
import json
import random
import time

SLEEP = 0.5

# ZMQ publisher setup
context = zmq.Context()
socket = context.socket(zmq.PUB)
socket.bind("tcp://*:5555")

while True:

    e1 = {
        "name": "vacuum",
        "ch": 1,
        "dev": "GJ_E1",
        "ldev": "gj_maxigauge",
        "value": round(random.uniform(5e-10, 1e-4), 8),
        "epoch_time": time.time(),
    }
    e2 = {
        "name": "vacuum",
        "ch": 2,
        "dev": "GJ_E2",
        "ldev": "gj_maxigauge",
        "value": round(random.uniform(5e-10, 1e-4), 8),
        "epoch_time": time.time(),
    }
    e3 = {
        "name": "vacuum",
        "ch": 3,
        "dev": "GJ_E3",
        "ldev": "gj_maxigauge",
        "value": round(random.uniform(5e-10, 1e-4), 8),
        "epoch_time": time.time(),
    }
    s1 = {
        "name": "vacuum",
        "ch": 4,
        "dev": "GJ_S1",
        "ldev": "gj_maxigauge",
        "value": round(random.uniform(5e-10, 1e-4), 8),
        "epoch_time": time.time(),
    }
    s2 = {
        "name": "vacuum",
        "ch": 5,
        "dev": "GJ_S2",
        "ldev": "gj_maxigauge",
        "value": round(random.uniform(5e-10, 1e-4), 8),
        "epoch_time": time.time(),
    }
    s3 = {
        "name": "vacuum",
        "ch": 6,
        "dev": "GJ_S3",
        "ldev": "gj_maxigauge",
        "value": round(random.uniform(5e-10, 1e-4), 8),
        "epoch_time": time.time(),
    }

    temperature1 = {
        "name": "temperature",
        "dev": "GJ_ColdheadT1",
        "ldev": "lakeshore",
        "ch": 1,
        "value": round(random.uniform(3, 300), 2),
        "epoch_time": time.time(),
    }

    temperature2 = {
        "name": "temperature",
        "dev": "GJ_ColdheadT2",
        "ldev": "lakeshore",
        "ch": 2,
        "value": round(random.uniform(3, 300), 2),
        "epoch_time": time.time(),
    }

    allofthem = {
        "s1": s1,
        "s2": s2,
        "s3": s3,
        "e1": e1,
        "e2": e2,
        "e3": e3,
        "temperature1": temperature1,
        "temperature2": temperature2,
    }

    message = json.dumps(allofthem)
    socket.send_string(message)
    print("\n", message)
    time.sleep(SLEEP)  # Adjust sleep time as needed
