import socket
import re
from loguru import logger


import os
import time
import sys
import argparse
import toml

SLEEP = 0.5

# Validate the TOML file
def validate_config(config):
    required_keys = [
        "tcu.address",
        "tcu.port",
        "lakeshore.sensor1",
        "lakeshore.sensor2",
        "lakeshore.address",
        "lakeshore.port",
        "multigauge.address",
        "multigauge.port",
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
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)  # Avoid getting stuck indefinitely
        s.connect((host, port))
        s.sendall(message.encode())  # Ensure newline for proper request termination
        
        try:
            response = s.recv(1024).decode()
        except socket.timeout:
            return "Timeout: No response received."

    # Extract numeric values using regex
    return float(re.sub(r'[^0-9.]', '', response))

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

    validate_arguments(args)

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
    lakeshore_sensor1 = config["lakeshore"]["sensor1"]
    lakeshore_sensor2 = config["lakeshore"]["sensor2"]
    lakeshore_address = config["lakeshore"]["address"]
    lakeshore_port = config["lakeshore"]["port"]

    multigauge_address = config["multigauge"]["address"]
    multigauge_port = config["multigauge"]["port"]
    
    # ZMQ setup
    #context = zmq.Context()

    while True:
        print(get_temperature(host=lakeshore_address, port=lakeshore_port, message=lakeshore_sensor1+'\n'))


# -------

if __name__ == "__main__":
    main()
