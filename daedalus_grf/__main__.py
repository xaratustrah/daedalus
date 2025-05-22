#!/usr/bin/env python
"""
Daedalus data aggregator and grafana/influx interface

Jan 2025 xaratustrah@github

"""

import zmq
import json
import toml
import os
import sys
import argparse
import random
import time
import threading
import requests
from loguru import logger
from influxdb_client import InfluxDBClient

# REST shared variables
shared_json1 = {}
shared_json2 = {}

# Validate the TOML file
def validate_config(config):
    required_keys = [
        "mcu.address",
        "mcu.port",
        "tcu.address",
        "tcu.port",
        "influx.address",
        "influx.port",
        "influx.org",
        "influx.bucket",
        "influx.token",
        "restapi.resturl1",
        "restapi.resturl2",
        "gas.species",
    ]
    for key in required_keys:
        keys = key.split(".")
        conf = config
        for k in keys:
            if k not in conf:
                raise ValueError(f"Missing required key: {key}")
            conf = conf[k]

def flatten_dict(d, parent_key="", sep="_"):
    items = []
    for k, v in d.items():
        if isinstance(v, dict):
            items.extend(flatten_dict(v, "", sep=sep).items())
        else:
            items.append((k, v))
    return dict(items)

def calculate_jet_velocity(temperature, nozzle_pressure):
    # meter per seconds
    # here comes the real forumla, for now just a random number
    return random.uniform(300, 1500)


def calculate_target_density(velocity, s1, s2, s3, s4):
    # particles per square centimeter
    # here comes the real forumla, for now just a random number
    return random.uniform(1.0e10, 1.0e13)

def validate_arguments(args):
    if args.log and not args.logfile:
        raise ValueError('Filename must be provided when logging is enabled')

# Function to update the first shared variable
def update_variable1(url):
    global shared_json1
    s = requests.Session()
    r = s.get(url, stream=True)
    for line in r.iter_lines():
        if line:
            byte_array_str = line.decode("utf-8")
            json_str = byte_array_str.replace("data: ", "")
            shared_json1 = json.loads(json_str)

# Function to update the second shared variable
def update_variable2(url):
    global shared_json2
    s = requests.Session()
    r = s.get(url, stream=True)
    for line in r.iter_lines():
        if line:
            byte_array_str = line.decode("utf-8")
            json_str = byte_array_str.replace("data: ", "")
            shared_json2 = json.loads(json_str)
       
def process_jsons(json1, json2):
    name1 = "GJ_S4"
    value1 = 0.1    
    epoch_time1 = 1
    
    name2 = "GJ_E4"
    value2 = 0.1  
    epoch_time2 = 1

    try:
        name1 = json1['sourceInfo']['deviceName']
        value1 = float(json1['data']['pressure']) / 100.0, # convert Pa to mbar
        if isinstance(value1, tuple): # sometimes the value is tuple, why?
            value1 = value1[0]
        epoch_time1 = float(json1['data']['timestampAcq'] / 1e9)
        
        name2 = json2['sourceInfo']['deviceName']
        value2 = float(json2['data']['pressure']) / 100.0, # convert Pa to mbar
        if isinstance(value2, tuple): # sometimes the value is tuple, why?
            value2 = value2[0]
        epoch_time2 = float(json2['data']['timestampAcq'] / 1e9)
                
    except(KeyError):
        pass # do nothing for now.

    s4 = {
        "name": "vacuum",
        "dev": "GJ_S4", # Identifier for measurement device
        "ldev": name1,  # Identifier for logging device
        "value": value1,
        "epoch_time": epoch_time1
    }
    e4 = {
        "name": "vacuum",
        "dev": "GJ_E4", # Identifier for measurement device
        "ldev": name2,  # Identifier for logging device
        "value": value2,
        "epoch_time": epoch_time2
    }

    return {
        "s4": s4,
        "e4": e4,
    }

def update_epoch_time(data):
    right_now = time.time()
    if isinstance(data, dict):  # If it's a dictionary
        for key, value in data.items():
            if key == "epoch_time":
                data[key] = right_now  # Update value
            else:
                update_epoch_time(value)  # Recurse into sub-elements
    elif isinstance(data, list):  # If it's a list
        for item in data:
            update_epoch_time(item)  # Recurse into each list item

    return data
         
def main():
    logger.remove(0)
    logger.add(sys.stdout, level="INFO")

    parser = argparse.ArgumentParser(
        description="Daedalus GRF: Data aggregator for the Daedalus Project."
    )
    parser.add_argument(
        "--cfg", type=str, required=True, help="Path to the configuration TOML file."
    )
    
    parser.add_argument('--debug', action='store_true', help='Enable debugging mode')
    parser.add_argument('--log', action='store_true', help='Enable logging mode')
    parser.add_argument('--logfile', type=str, help='Log file name')

    args = parser.parse_args()

    try:
        validate_arguments(args)
    except ValueError as e:
        logger.error(f'{e}. Aborting...')
        sys.exit(1)

    if args.debug:
        logger.info('Debugging mode is enabled')
    if args.log:
        logger.info(f'Logging to file: {args.logfile}')


    # Read and validate the configuration from the TOML file
    config_path = args.cfg
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"TOML file not found: {config_path}")

    config = toml.load(config_path)
    validate_config(config)

    # Extract socket information from the configuration
    mcu_address = config["mcu"]["address"]
    mcu_port = config["mcu"]["port"]
    tcu_address = config["tcu"]["address"]
    tcu_port = config["tcu"]["port"]
    
    influx_url=f'{config["influx"]["address"]}:{config["influx"]["port"]}'
    influx_token = config["influx"]["token"]
    influx_org = config["influx"]["org"]
    influx_bucket = config["influx"]["bucket"]

    restapi_resturl1 = config["restapi"]["resturl1"]
    restapi_resturl2 = config["restapi"]["resturl2"]
    
    gas_species = config["gas"]["species"]
    
    # ZMQ setup
    context = zmq.Context()

    socket_mcu = context.socket(zmq.SUB)
    socket_mcu.connect(f"{mcu_address}:{mcu_port}")
    socket_mcu.setsockopt_string(zmq.SUBSCRIBE, "")
    socket_mcu.setsockopt(zmq.CONFLATE, 1)  # Keep only the most recent message

    socket_tcu = context.socket(zmq.SUB)
    socket_tcu.connect(f"{tcu_address}:{tcu_port}")
    socket_tcu.setsockopt_string(zmq.SUBSCRIBE, "")
    socket_tcu.setsockopt(zmq.CONFLATE, 1)  # Keep only the most recent message
    
    # REST API
    # Create and start the first thread
    update_thread1 = threading.Thread(target=update_variable1, kwargs={'url' : restapi_resturl1})
    update_thread1.daemon = True  # Daemon thread will exit when the main program exits
    update_thread1.start()

    # Create and start the second thread
    update_thread2 = threading.Thread(target=update_variable2, kwargs={'url' : restapi_resturl2})
    update_thread2.daemon = True  # Daemon thread will exit when the main program exits
    update_thread2.start()

    while True:
        try:
            message_mcu = socket_mcu.recv_string()
            data_mcu = json.loads(message_mcu)

            message_tcu = socket_tcu.recv_string()
            data_tcu = json.loads(message_tcu)

            json_from_rest = process_jsons(shared_json1, shared_json2)
            combined_json = data_tcu | data_mcu | json_from_rest

            s1 = combined_json.get("s1")["value"]
            s2 = combined_json.get("s2")["value"]
            s3 = combined_json.get("s3")["value"]
            s4 = combined_json.get("s4")["value"]
            
            nozzle_pressure = combined_json.get("nozzle_pressure")["value"]
            
            # take temperature Cold head T1 for calculations
            temperature = combined_json.get("temperature1")["value"]

            velocity = calculate_jet_velocity(temperature, nozzle_pressure)
            density = calculate_target_density(velocity, s1, s2, s3, s4)

            calculated_json = {
                # "velocity": {
                #     "name": "velocity",
                #     "dev":"GJ",
                #     "value": velocity,
                #     "epoch_time": time.time(),
                # },
                "density": {
                    "name": "density",
                    "dev":"GJ",
                    #"species": gas_species,
                    #"value": density,
                    "value": f'{density},species="{gas_species}"',
                    "epoch_time": time.time()
                },
            }

            final_json = combined_json | calculated_json
            
            final_json = update_epoch_time(final_json)
            
            string_list = []
            
            for key, value in final_json.items():
                flat_dict = flatten_dict(value)
                flat_string = ",".join([f"{k}={v}" for k, v in flat_dict.items()])
                flat_string = flat_string.replace("name=", "").replace(",value", " value").replace(",epoch_time=", " ")
                flat_string = flat_string[:flat_string.rfind(".")]
            #    logger.info(flat_string)
                string_list.append(flat_string)

            single_string = "\n".join(string_list)                
            with InfluxDBClient(url=influx_url, token=influx_token, debug=args.debug) as client:
                with client.write_api() as writer:
                    writer.write(bucket=influx_bucket, org=influx_org, record=single_string, write_precision="s")
                            
            if args.log:
                with open(f'{args.logfile}', 'a') as f:
                    f.write(single_string + "\n")
                        
        except (EOFError, KeyboardInterrupt):
            logger.success("\nUser input cancelled. Aborting...")
            break


# -------

if __name__ == "__main__":
    main()
