"""
Daedalus unified system

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

import json
import toml
import argparse
import random
import time
import threading
import requests
from loguru import logger
from influxdb_client import InfluxDBClient
import re
#import socket
#import zmq

import RPi.GPIO as GPIO
import spidev

from voreas.tools import get_density_value

from .lakeshore import Lakeshore

# REST shared variables
shared_json1 = {}
shared_json2 = {}

# Validate the TOML file
def validate_config(config):
    required_keys = [
        "uni.update_rate",
        "influx.address",
        "influx.port",
        "influx.org",
        "influx.bucket",
        "influx.token",
        "restapi.resturl1",
        "restapi.resturl2",
        "gas.species",
        "lakeshore.sensor1",
        "lakeshore.sensor2",
        "lakeshore.address",
        "lakeshore.port",
        "maxigauge.address",
        "maxigauge.port",
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

def flatten_dict(d, parent_key="", sep="_"):
    items = []
    for k, v in d.items():
        if isinstance(v, dict):
            items.extend(flatten_dict(v, "", sep=sep).items())
        else:
            items.append((k, v))
    return dict(items)

# Function to update the first shared variable
def update_restapi1(url):
    global shared_json1
    s = requests.Session()
    r = s.get(url, stream=True)
    for line in r.iter_lines():
        if line:
            byte_array_str = line.decode("utf-8")
            json_str = byte_array_str.replace("data: ", "")
            shared_json1 = json.loads(json_str)

# Function to update the second shared variable
def update_restapi2(url):
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

# ---------- main function
         
def main():
    logger.remove(0)
    logger.add(sys.stdout, level="INFO")

    parser = argparse.ArgumentParser(
        description="Daedalus UNI: Unified entry point for the Daedalus project."
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

    uni_update_rate = config['uni']['update_rate']
    
    influx_url=f'{config["influx"]["address"]}:{config["influx"]["port"]}'
    influx_token = config["influx"]["token"]
    influx_org = config["influx"]["org"]
    influx_bucket = config["influx"]["bucket"]

    restapi_resturl1 = config["restapi"]["resturl1"]
    restapi_resturl2 = config["restapi"]["resturl2"]
    
    gas_species = config["gas"]["species"]

    lakeshore_sensor1 = config["lakeshore"]["sensor1"]
    lakeshore_sensor2 = config["lakeshore"]["sensor2"]
    lakeshore_address = config["lakeshore"]["address"]
    lakeshore_port = config["lakeshore"]["port"]

    maxigauge_address = config["maxigauge"]["address"]
    maxigauge_port = config["maxigauge"]["port"]
    
    
    nozzle_sensor_cal_points = config['nozzle_sensor']['cal_points']

    mcp3208_0_spi_bus = config['mcp3208_0']['spi_bus']
    mcp3208_0_spi_cs = config['mcp3208_0']['spi_cs']
    mcp3208_0_spi_max_speed_hz = config['mcp3208_0']['spi_max_speed_hz']
    mcp3208_0_num_average = config['mcp3208_0']['num_average']

    pot_x_cal_points = config['pot_x']['cal_points']
    pot_z_cal_points = config['pot_z']['cal_points']

    
    # REST API
    # Create and start the first thread
    restapi_thread1 = threading.Thread(target=update_restapi1, kwargs={'url' : restapi_resturl1})
    restapi_thread1.daemon = True  # Daemon thread will exit when the main program exits
    restapi_thread1.start()

    # Create and start the second thread
    restapi_thread2 = threading.Thread(target=update_restapi2, kwargs={'url' : restapi_resturl2})
    restapi_thread2.daemon = True  # Daemon thread will exit when the main program exits
    restapi_thread2.start()

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


    # initial value for density
    density = 0
    
    while True:
        try:
            # TCU Jsons
            
            try:
                t1_val_tmp = lakeshore.get_temperature(message=lakeshore_sensor1)
                t1_val = t1_val_tmp if t1_val_tmp != 0 else t1_val

                t2_val_tmp = lakeshore.get_temperature(message=lakeshore_sensor2)
                t2_val = t2_val_tmp if t2_val_tmp != 0 else t2_val

            except:
                pass
            
            try:
                e1_val, e2_val, e3_val, s3_val, s2_val, s1_val = get_pressures(maxigauge_address, maxigauge_port)
            except ConnectionResetError as e:
                logger.error(f"{e}. Ignoring...")        
            
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

            data_tcu = {
                "s1": s1,
                "s2": s2,
                "s3": s3,
                "e1": e1,
                "e2": e2,
                "e3": e3,
                "temperature1": temperature1,
                "temperature2": temperature2,
            }
            
            # MCU JSONs

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

            data_mcu = {
                "xpos": xpos,
                "zpos": zpos,
                "nozzle_pressure": nozzle_pressure,
                "shutter_signal": shutter_signal,
                "shutter_sensor": shutter_sensor,
            }

            # GRF JSONS

            json_from_rest = process_jsons(shared_json1, shared_json2)
            combined_json = data_tcu | data_mcu | json_from_rest

            s1 = combined_json.get("s1")["value"]
            s2 = combined_json.get("s2")["value"]
            s3 = combined_json.get("s3")["value"]
            s4 = combined_json.get("s4")["value"]
            
            nozzle_pressure = combined_json.get("nozzle_pressure")["value"]
            
            # take temperature Cold head T1 for calculations
            temperature = combined_json.get("temperature1")["value"]

            # calculate density
            try:
                density = get_density_value(name = gas_species, T = temperature, p = nozzle_pressure, S1 = s1, S2 = s2, S3 = s3, S4 = s4)
            except:
                logger.error("\nSome issues encountered during density calculation. Ignoring...")


            calculated_json = {
                "density": {
                    "name": "density",
                    "dev":"GJ",
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
                    #f.write(single_string + "\n")
                    f.write(json.dumps(final_json) + "\n")
                        
            time.sleep(uni_update_rate)
            
        except (EOFError, KeyboardInterrupt):
            logger.success("\nUser input cancelled. Aborting...")
            GPIO.cleanup()
            mcp3208_0_spi_obj.close()
            lakeshore.close()
            break


# -------

if __name__ == "__main__":
    main()
