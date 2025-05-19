"""
Daedalus motor controller unit

2025 xaratustrah@github
"""

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
        "mcu.address",
        "mcu.port",
        "mcu.update_rate",
        "mcu.num_average",
        "nozpressure.cal_points",
        "mcp23s08_0.spi_bus",
        "mcp23s08_0.spi_cs",
        "mcp23s08_0.spi_max_speed_hz",
        "mcp23s08_0.cs_pin",
        "mcp23s08_1.spi_bus",
        "mcp23s08_1.spi_cs",
        "mcp23s08_1.spi_max_speed_hz",
        "mcp23s08_1.cs_pin",
        "mcp3208_0.spi_bus",
        "mcp3208_0.spi_cs",
        "mcp3208_0.spi_max_speed_hz",
        "mcp3208_0.cs_pin",
        "mcp3208_1.spi_bus",
        "mcp3208_1.spi_cs",
        "mcp3208_1.spi_max_speed_hz",
        "mcp3208_1.cs_pin",
    ]

    for key in required_keys:
        keys = key.split(".")
        conf = config
        for k in keys:
            if k not in conf:
                raise ValueError(f"Missing required key: {key}")
            conf = conf[k]
            
# -------

def main():
    logger.remove(0)
    logger.add(sys.stdout, level="INFO")

    parser = argparse.ArgumentParser(
        description="Daedalus MCU: Motor controller unit for the Daedalus project."
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

    # Extract information from the configuration
    self.mcu_address = config['mcu']['address']
    self.mcu_port = config['mcu']['port']
    self.mcu_update_rate = config['mcu']['update_rate']
    self.mcu_num_average = config['mcu']['num_average']

    self.nozpressure_cal_points = config['nozpressure']['cal_points']

    self.mcp23s08_0_spi_bus = config['mcp23s08_0']['spi_bus']
    self.mcp23s08_0_spi_cs = config['mcp23s08_0']['spi_cs']
    self.mcp23s08_0_spi_max_speed_hz = config['mcp23s08_0']['spi_max_speed_hz']
    self.mcp23s08_0_cs_pin = config['mcp23s08_0']['cs_pin']

    self.mcp23s08_1_spi_bus = config['mcp23s08_1']['spi_bus']
    self.mcp23s08_1_spi_cs = config['mcp23s08_1']['spi_cs']
    self.mcp23s08_1_spi_max_speed_hz = config['mcp23s08_1']['spi_max_speed_hz']
    self.mcp23s08_1_cs_pin = config['mcp23s08_1']['cs_pin']

    self.mcp3208_0_spi_bus = config['mcp3208_0']['spi_bus']
    self.mcp3208_0_spi_cs = config['mcp3208_0']['spi_cs']
    self.mcp3208_0_spi_max_speed_hz = config['mcp3208_0']['spi_max_speed_hz']
    self.mcp3208_0_cs_pin = config['mcp3208_0']['cs_pin']

    self.mcp3208_1_spi_bus = config['mcp3208_1']['spi_bus']
    self.mcp3208_1_spi_cs = config['mcp3208_1']['spi_cs']
    self.mcp3208_1_spi_max_speed_hz = config['mcp3208_1']['spi_max_speed_hz']
    self.mcp3208_1_cs_pin = config['mcp3208_1']['cs_pin']

    # ZMQ publisher setup
    context = zmq.Context()
    zmq_socket = context.socket(zmq.PUB)
    zmq_full_adr = f"{mcu_address}:{mcu_port}"
    logger.info(f"Connecting ZMQ publisher to: {zmq_full_adr}")
    zmq_socket.bind(zmq_full_adr)

    # main loop
    
    while True:
        try:
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

            allofthem = {
                "xpos": xpos,
                "ypos": ypos,
                "zpos": zpos,
                "nozzle_pressure": nozzle_pressure,
                "shutter_signal": shutter_signal,
                "shutter_sensor": shutter_sensor,
            }

            message = json.dumps(allofthem)
            socket.send_string(message)
            print("\n", message)
            time.sleep(mcu_update_rate)  # Adjust sleep time as needed

        except (EOFError, KeyboardInterrupt):
            logger.success("\nUser input cancelled. Aborting...")
            break

# -------

if __name__ == "__main__":
    main()
