"""
Daedalus motor controller unit

2025 xaratustrah@github
"""

import os
import sys

def is_raspberry_pi():
    try:
        with open("/proc/device-tree/model", "r") as model_file:
            if "Raspberry Pi" in model_file.read():
                return True
    except FileNotFoundError:
        pass
    return False

if not is_raspberry_pi():
    print("This code is designed for a Raspberry Pi.")
    sys.exit(1)

import socket
import re
from loguru import logger
import zmq
import time
import argparse
import toml
import random
import json

from piadcio.mcp23s08 import MCP23S08
from piadcio.mcp3208 import MCP3208

# Define LED pins
LED1 = 0
LED2 = 0


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

def validate_arguments(args):
    if args.log and not args.logfile:
        raise ValueError('Filename must be provided when logging is enabled')
        
def decode_mcp23s08_reg(reg_value):
    """Returns a list representing the state of 8 GPIO pins (True for HIGH, False for LOW)."""    
    state_vector = [(reg_value >> i) & 1 == 1 for i in range(8)]
    return state_vector
  
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
    mcu_address = config['mcu']['address']
    mcu_port = config['mcu']['port']
    mcu_update_rate = config['mcu']['update_rate']
    mcu_num_average = config['mcu']['num_average']

    nozpressure_cal_points = config['nozpressure']['cal_points']

    mcp23s08_0_spi_bus = config['mcp23s08_0']['spi_bus']
    mcp23s08_0_spi_cs = config['mcp23s08_0']['spi_cs']
    mcp23s08_0_spi_max_speed_hz = config['mcp23s08_0']['spi_max_speed_hz']
    mcp23s08_0_cs_pin = config['mcp23s08_0']['cs_pin']

    mcp23s08_1_spi_bus = config['mcp23s08_1']['spi_bus']
    mcp23s08_1_spi_cs = config['mcp23s08_1']['spi_cs']
    mcp23s08_1_spi_max_speed_hz = config['mcp23s08_1']['spi_max_speed_hz']
    mcp23s08_1_cs_pin = config['mcp23s08_1']['cs_pin']

    mcp3208_0_spi_bus = config['mcp3208_0']['spi_bus']
    mcp3208_0_spi_cs = config['mcp3208_0']['spi_cs']
    mcp3208_0_spi_max_speed_hz = config['mcp3208_0']['spi_max_speed_hz']
    mcp3208_0_cs_pin = config['mcp3208_0']['cs_pin']

    mcp3208_1_spi_bus = config['mcp3208_1']['spi_bus']
    mcp3208_1_spi_cs = config['mcp3208_1']['spi_cs']
    mcp3208_1_spi_max_speed_hz = config['mcp3208_1']['spi_max_speed_hz']
    mcp3208_1_cs_pin = config['mcp3208_1']['cs_pin']


    adc0 = MCP3208(
        config["mcp3208_0"]["spi_bus"],
        config["mcp3208_0"]["spi_cs"],
        config["mcp3208_0"]["spi_max_speed_hz"],
        config["mcp3208_0"]["cs_pin"]
    )

    adc1 = MCP3208(
        config["mcp3208_1"]["spi_bus"],
        config["mcp3208_1"]["spi_cs"],
        config["mcp3208_1"]["spi_max_speed_hz"],
        config["mcp3208_1"]["cs_pin"]
    )


    ioexp0 = MCP23S08(
        config["mcp23s08_0"]["spi_bus"],
        config["mcp23s08_0"]["spi_cs"],
        config["mcp23s08_0"]["spi_max_speed_hz"],
        config["mcp23s08_0"]["cs_pin"]
    )
    
    ioexp1 = MCP23S08(
        config["mcp23s08_1"]["spi_bus"],
        config["mcp23s08_1"]["spi_cs"],
        config["mcp23s08_1"]["spi_max_speed_hz"],
        config["mcp23s08_1"]["cs_pin"]
    )
    
    ioexp0.set_direction(0xfe) # Set all pins as inputs except the pin 0 for the LED
    ioexp1.set_direction(0xfe) # Set all pins as inputs except the pin 0 for the LED

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
            zmq_socket.send_string(message)
            print("\n", message)
            
            num = ioexp0.read_all_gpio_pins()
            print(f'ioexp0: {decode_mcp23s08_reg(num)}')
            
            num = ioexp1.read_all_gpio_pins()
            print(f'ioexp1: {decode_mcp23s08_reg(num)}')

            time.sleep(mcu_update_rate)

        except (EOFError, KeyboardInterrupt):
            logger.success("\nUser input cancelled. Aborting...")
            ioexp0.close()
            ioexp1.close()
            adc0.close()
            adc1.close()
            
            break

# -------

if __name__ == "__main__":
    main()
