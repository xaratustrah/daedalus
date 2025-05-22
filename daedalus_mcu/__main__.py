"""
Daedalus motor controller unit

2025 xaratustrah@github
"""

import os
import sys

# if not raspberry pi, stop here.
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

import RPi.GPIO as GPIO
import spidev

def validate_config(config):
    required_keys = [
        "mcu.address",
        "mcu.port",
        "mcu.update_rate",
        "nozzle_sensor.cal_points",
        "mcp3208_0.spi_bus",
        "mcp3208_0.spi_cs",
        "mcp3208_0.spi_max_speed_hz",
        "mcp3208_0.num_average",
        "pot_x.cal_points",
        "pot_z.cal_points",
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

def adc_to_voltage(adc_value, adc_range=4095, voltage_range=3.3):
    """Convert ADC value to voltage."""
    return (adc_value / adc_range) * voltage_range

def voltage_to_pressure(voltage, cal_points):
    """Convert voltage to pressure (mbar) using linear interpolation, clipped to 0-60 mbar."""
    v1, v2 = cal_points[0]  # Voltage points
    p1, p2 = cal_points[1]  # Corresponding pressure points

    # Linear interpolation formula
    pressure = p1 + (voltage - v1) * (p2 - p1) / (v2 - v1)

    # Clipping the pressure value to be within [0, 60] range
    return max(p1, min(pressure, p2))

def voltage_to_position(voltage, cal_points):
    """Convert voltage to position (mm) using linear interpolation, clipped to the defined range."""
    v1, v2 = cal_points[0]  # Voltage points
    pos1, pos2 = cal_points[1]  # Corresponding position points

    # Linear interpolation formula
    position = pos1 + (voltage - v1) * (pos2 - pos1) / (v2 - v1)

    # Clipping the position value within the defined range
    return position

def toggle_led():
    """Toggle the LED state."""
    global led_state
    led_state = not led_state
    GPIO.output(LED_PIN, led_state)

def read_adc_channel(spi, channel):
    (msg_up, msg_dn) = (
        (0x06, 0x00) if channel == 0
        else (0x06, 0x40) if channel == 1
        else (0x06, 0x80) if channel == 2
        else (0x06, 0xC0) if channel == 3
        else (0x07, 0x00) if channel == 4
        else (0x07, 0x40) if channel == 5
        else (0x07, 0x80) if channel == 6
        else (0x07, 0xC0)
    )

    resp = spi.xfer([msg_up, msg_dn, 0x00])
    value = (resp[1] << 8) + resp[2]
    value = int(value)

    # clip value
    if value <= 0:
        value = 0
    elif value > 4095:
        value = 4095

    return value

def read_all_adc_channels(spi, num_average):
    
    ch0, ch1, ch2, ch3, ch4, ch5, ch6, ch7 = 0, 0, 0, 0, 0, 0, 0, 0
    # do many measurements and average
    for i in range(num_average):
        ch0 += read_adc_channel(spi, 0)
        ch1 += read_adc_channel(spi, 1)
        ch2 += read_adc_channel(spi, 2)
        ch3 += read_adc_channel(spi, 3)
        ch4 += read_adc_channel(spi, 4)
        ch5 += read_adc_channel(spi, 5)
        ch6 += read_adc_channel(spi, 6)
        ch7 += read_adc_channel(spi, 7)
    return [
        int(ch0 / num_average),
        int(ch1 / num_average),
        int(ch2 / num_average),
        int(ch3 / num_average),
        int(ch4 / num_average),
        int(ch5 / num_average),
        int(ch6 / num_average),
        int(ch7 / num_average),
    ]

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
    mcu_address = config['mcu']['address']
    mcu_port = config['mcu']['port']
    mcu_update_rate = config['mcu']['update_rate']

    nozzle_sensor_cal_points = config['nozzle_sensor']['cal_points']

    mcp3208_0_spi_bus = config['mcp3208_0']['spi_bus']
    mcp3208_0_spi_cs = config['mcp3208_0']['spi_cs']
    mcp3208_0_spi_max_speed_hz = config['mcp3208_0']['spi_max_speed_hz']
    mcp3208_0_num_average = config['mcp3208_0']['num_average']

    pot_x_cal_points = config['pot_x']['cal_points']
    pot_z_cal_points = config['pot_z']['cal_points']
    
    # ZMQ publisher setup
    context = zmq.Context()
    zmq_socket = context.socket(zmq.PUB)
    zmq_full_adr = f"{mcu_address}:{mcu_port}"
    logger.info(f"Connecting ZMQ publisher to: {zmq_full_adr}")
    zmq_socket.bind(zmq_full_adr)

    # Setup GPIO
    PINS = [16, 18, 22, 32, 33, 37]
    LED_PIN = 31  # LED pin

    GPIO.setwarnings(False)  # Suppress warnings
    GPIO.setmode(GPIO.BOARD)  # Use BOARD numbering
    for pin in PINS:
        GPIO.setup(pin, GPIO.IN)  # Set pins as inputs
    GPIO.setup(LED_PIN, GPIO.OUT)  # Set LED pin as output

    # LED state variable
    led_state = False

    # setup SPI
    mcp3208_0_spi_obj = spidev.SpiDev()
    mcp3208_0_spi_obj.open(mcp3208_0_spi_bus, mcp3208_0_spi_cs)
    mcp3208_0_spi_obj.max_speed_hz = mcp3208_0_spi_max_speed_hz

    # main loop
    while True:
        try:

            # Read out digital inputs            
            digital_input_vector = [bool(GPIO.input(pin)) for pin in PINS]
            
            # sensor value has to be negated because sensor gives HI when shutter is out
            digital_input_vector[5] = not digital_input_vector[5]
            
            (
                motx_lim_ring_outside,
                motx_lim_ring_inside,
                motz_lim_downstream,
                motz_lim_upstream,
                shutter_signal_value,
                shutter_sensor_value
            ) = digital_input_vector
            
            led_state = not led_state
            GPIO.output(LED_PIN, led_state)
            
            # Read out analog inputs            
            analog_input_vector = read_all_adc_channels(mcp3208_0_spi_obj, mcp3208_0_num_average)
            (
                potx_raw,
                potz_raw,
                nozzle_pressure_raw
            ) = analog_input_vector[0:3]
            
            nozzle_pressure_value = voltage_to_pressure(adc_to_voltage(nozzle_pressure_raw), nozzle_sensor_cal_points)

            potx_value = voltage_to_position(adc_to_voltage(potx_raw), pot_x_cal_points)
            potz_value = voltage_to_position(adc_to_voltage(potz_raw), pot_z_cal_points)

            # print(nozzle_sensor_cal_points)
            # print(f"Digital: {digital_input_vector}")

            # print(f'potx: (raw={potx_raw}, val={potx_value:.3f} mm)\n'
            #       f'potz: (raw={potz_raw}, val={potz_value:.3f} mm)\n'
            #       f'nozzle_pressure: (raw={nozzle_pressure_raw}, val={nozzle_pressure_value:.3f} bar)')
                     
            if motx_lim_ring_outside or motx_lim_ring_inside:            
                xpos = {
                    "name": "position",
                    "ch": "x",
                    "dev": "nozzle",
                    "ldev": "daedalus",
                    "limit_plus" : motx_lim_ring_outside,
                    "limit_minus" : motx_lim_ring_inside,
                    "raw": potx_raw,
                    "value": potx_value,
                    "epoch_time": time.time(),
                }
            else:
                xpos = {
                    "name": "position",
                    "ch": "x",
                    "dev": "nozzle",
                    "ldev": "daedalus",
                    "raw": potx_raw,
                    "value": potx_value,
                    "epoch_time": time.time(),
                }

            if motz_lim_downstream or motz_lim_upstream:            
                zpos = {
                "name": "position",
                "ch": "z",
                "dev": "nozzle",
                "ldev": "daedalus",
                "limit_plus" : motz_lim_downstream,
                "limit_minus" : motz_lim_upstream,
                "raw": potz_raw,
                "value": potz_value,
                "epoch_time": time.time(),
                }
            else:
                zpos = {
                "name": "position",
                "ch": "z",
                "dev": "nozzle",
                "ldev": "daedalus",
                "raw": potz_raw,
                "value": potz_value,
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
                "value": shutter_signal_value,
                "epoch_time": time.time(),
            }

            shutter_sensor = {
                "name": "shutter",
                "ch": "0",
                "dev": "nozzle",
                "ldev": "daedalus",
                "type": "sensor",
                "value": shutter_sensor_value,
                "epoch_time": time.time(),
            }

            allofthem = {
                "xpos": xpos,
                "zpos": zpos,
                "nozzle_pressure": nozzle_pressure,
                "shutter_signal": shutter_signal,
                "shutter_sensor": shutter_sensor,
            }

            message = json.dumps(allofthem)
            zmq_socket.send_string(message)

            if args.debug:
                print("\n", message)
            
            if args.log:
                with open(f'{args.logfile}', 'a') as f:
                    f.write(message + "\n")

            # wait
            time.sleep(mcu_update_rate)

        except (EOFError, KeyboardInterrupt):
            logger.success("\nUser input cancelled. Aborting...")
            GPIO.cleanup()
            mcp3208_0_spi_obj.close()
            break

# -------

if __name__ == "__main__":
    main()
