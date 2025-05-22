import socket
import re
from loguru import logger
import zmq
import os
import time
import sys
import argparse
import toml
import random
import json

def validate_config(config):
    required_keys = [
        "tcu.address",
        "tcu.port",
        "tcu.update_rate",
        "lakeshore.sensor1",
        "lakeshore.sensor2",
        "lakeshore.address",
        "lakeshore.port",
        "maxigauge.address",
        "maxigauge.port",
    ]
    for key in required_keys:
        keys = key.split(".")
        conf = config
        for k in keys:
            if k not in conf:
                raise ValueError(f"Missing required key: {key}")
            conf = conf[k]

def validate_arguments(args):
    if args.log and not args.logfile:
        raise ValueError('Filename must be provided when logging is enabled')

def get_temperature(host, port, message, timeout=2):
    temp = 0
 
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            #s.settimeout(timeout)  # Avoid getting stuck indefinitely
            s.connect((host, port))
            s.sendall(message.encode())  # Ensure newline for proper request termination
            
            response = s.recv(1024).decode()
            
            if not response:  # Ensure data is received
                raise ValueError(f"No incoming data?")
            
            temp = float(re.sub(r'[^0-9.]', '', response))
            time.sleep(1)  # Wait exactly 1 seconds before closing (like nc -q 1)
        # Socket automatically closes at the end of the "with" block
             
    except (socket.timeout, socket.error, ValueError) as e:
        logger.error(f"While reading temperature: {e}. Will try again.")

    # Extract numeric values using regex
    return temp

def get_pressures(host, port, timeout=2):
    e1, e2, e3, s3, s2, s1 = [0] * 6  # Initialize values

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            # timeout is not needed, I keep it here.
            #s.settimeout(timeout)
            s.connect((host, port))

            response = s.recv(1024).decode()  # This may raise ConnectionResetError

            if not response:  # Ensure data is received
                raise ValueError(f"No incoming data?")

            lines = response.split("\r\n")

            for line in lines:
                lst = line.split(',')
                if len(lst) == 12:
                    e1, e2, e3, s3, s2, s1 = (lst[i] for i in range(1, len(lst), 2))

    except (socket.timeout, socket.error, ValueError) as e:
        logger.error(f"While reading pressures: {e}. Will try again.")

    return tuple(map(float, (e1, e2, e3, s3, s2, s1)))

# -------

def main():
    logger.remove(0)
    logger.add(sys.stdout, level="INFO")

    parser = argparse.ArgumentParser(
        description="Daedalus TCU: Pressure and temperature reader for the Daedalus Project."
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

    # Extract information from the configuration
    tcu_address = config["tcu"]["address"]
    tcu_port = config["tcu"]["port"]
    tcu_update_rate = config["tcu"]["update_rate"]
    
    lakeshore_sensor1 = config["lakeshore"]["sensor1"]
    lakeshore_sensor2 = config["lakeshore"]["sensor2"]
    lakeshore_address = config["lakeshore"]["address"]
    lakeshore_port = config["lakeshore"]["port"]

    maxigauge_address = config["maxigauge"]["address"]
    maxigauge_port = config["maxigauge"]["port"]
    
    # ZMQ publisher setup
    context = zmq.Context()
    zmq_socket = context.socket(zmq.PUB)
    zmq_full_adr = f"{tcu_address}:{tcu_port}"
    logger.info(f"Connecting ZMQ publisher to: {zmq_full_adr}")
    zmq_socket.bind(zmq_full_adr)

    # initialize variables with zero for any case
    t1_val, t2_val, e1_val, e2_val, e3_val, s1_val, s2_val, s3_val = [0] * 8
    
    while True:
        try:
            # get values:
                
            # the endline character is important at the end!
            t1_val = get_temperature(host=lakeshore_address, port=lakeshore_port, message=lakeshore_sensor1+'\n')
            t2_val = get_temperature(host=lakeshore_address, port=lakeshore_port, message=lakeshore_sensor2+'\n')

            try:
                e1_val, e2_val, e3_val, s3_val, s2_val, s1_val = get_pressures(maxigauge_address, maxigauge_port)
            except ConnectionResetError as e:
                logger.error(f"{e}. Ignoring...")        
            # test values
            # e1_val = round(random.uniform(5e-10, 1e-4), 8)
            # e2_val = round(random.uniform(5e-10, 1e-4), 8)
            # e3_val = round(random.uniform(5e-10, 1e-4), 8)
            # s3_val = round(random.uniform(5e-10, 1e-4), 8)
            # s2_val = round(random.uniform(5e-10, 1e-4), 8)
            # s1_val = round(random.uniform(5e-10, 1e-4), 8)
            
            e1 = {
                "name": "vacuum",
                "ch": 1,
                "dev": "GJ_E1",
                "ldev": "gj_maxigauge",
                "value": e1_val,
                "epoch_time": time.time(),
            }
            e2 = {
                "name": "vacuum",
                "ch": 2,
                "dev": "GJ_E2",
                "ldev": "gj_maxigauge",
                "value": e2_val,
                "epoch_time": time.time(),
            }
            e3 = {
                "name": "vacuum",
                "ch": 3,
                "dev": "GJ_E3",
                "ldev": "gj_maxigauge",
                "value": e3_val,
                "epoch_time": time.time(),
            }
            s1 = {
                "name": "vacuum",
                "ch": 4,
                "dev": "GJ_S1",
                "ldev": "gj_maxigauge",
                "value": s1_val,
                "epoch_time": time.time(),
            }
            s2 = {
                "name": "vacuum",
                "ch": 5,
                "dev": "GJ_S2",
                "ldev": "gj_maxigauge",
                "value": s2_val,
                "epoch_time": time.time(),
            }
            s3 = {
                "name": "vacuum",
                "ch": 6,
                "dev": "GJ_S3",
                "ldev": "gj_maxigauge",
                "value": s3_val,
                "epoch_time": time.time(),
            }

            temperature1 = {
                "name": "temperature",
                "dev": "GJ_ColdheadT1",
                "ldev": "lakeshore",
                "ch": 1,
                "value": t1_val,
                "epoch_time": time.time(),
            }

            temperature2 = {
                "name": "temperature",
                "dev": "GJ_ColdheadT2",
                "ldev": "lakeshore",
                "ch": 2,
                "value": t2_val,
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
            zmq_socket.send_string(message)
            
            if args.debug:
                print("\n", message)

            if args.log:
                with open(f'{args.logfile}', 'a') as f:
                    f.write(message + "\n")

            time.sleep(tcu_update_rate)

        except (EOFError, KeyboardInterrupt):
            logger.success("\nUser input cancelled. Aborting...")
            break


# -------

if __name__ == "__main__":
    main()
