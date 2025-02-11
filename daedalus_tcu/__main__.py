import socket
import os
import time
import sys
import argparse
import toml

def main():

    # Parse the location of the TOML config file given at the command line
    parser = argparse.ArgumentParser(
        description="Subscriber script with TOML config"
    )

    parser.add_argument(
        "--cfg", type=str, required=True, help="Path to TOML config file."
    )

    args = parser.parse_args()

    # Read config info from the TOML file
    config_path = args.cfg
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"TOML file not found: {config_path}")
    
    config = toml.load(config_path)

    # Extract info from TOML config
    tcu_address = config["tcu"]["address"]
    tcu_port = config["tcu"]["port"]
    
    token = config["grafana"]["token"]
    bucket = config["grafana"]["bucket"]
    org = config["grafana"]["org"]

    lakeshore1_sensor = config["lakeshore"]["sensor1"]
    lakeshore2_sensor = config["lakeshore"]["sensor2"]
    lakeshore_address = config["lakeshore"]["address"]
    lakeshore_port = config["lakeshore"]["port"]

    # labels for data values
    labels = ["vacuum,dev=GJ_E1,ldev=gj_maxigauge,ch=1 value=",
              "vacuum,dev=GJ_E2,ldev=gj_maxigauge,ch=2 value=",
              "vacuum,dev=GJ_E3,ldev=gj_maxigauge,ch=3 value=",
              "vacuum,dev=GJ_S3,ldev=gj_maxigauge,ch=4 value=",
              "vacuum,dev=GJ_S2,ldev=gj_maxigauge,ch=5 value=",
              "vacuum,dev=GJ_S1,ldev=gj_maxigauge,ch=6 value=",
              "temperature,dev=GJ_ColdheadT1,ldev=lakeshore,ch=1 value=",
              "temperature,dev=GJ_ColdheadT2,ldev=lakeshore,ch=2 value="]

    sock = socket.socket()
    
    sock.connect((tcu_address, tcu_port))

    output_str = [""] * 8

    while True:

        grafana_str = f"curl -sS -XPOST -H \'Authorization: Token {token}\' \"yrfile1:8086/api/v2/write?org={org}&bucket={bucket}&precision=s\" --data-binary \""

        # get current local time in seconds since Unix epoch
        current_time = int(time.mktime(time.localtime()))

        # get temps from lakeshore
        current_temp1 = os.popen(f"echo {lakeshore1_sensor} | nc -q 1 {lakeshore_address} {lakeshore_port} | sed 's/[^0-9\.]*//g'").read()
        current_temp2 = os.popen(f"echo {lakeshore2_sensor} | nc -q 1 {lakeshore_address} {lakeshore_port} | sed 's/[^0-9\.]*//g'").read()

        vac_input_str = sock.recv(1024)
        print(vac_input_str)

        # get vacuum info and add to output_str
        for i in range(6):
            output_str[i]=str(vac_input_str[3+i*14:3+i*14+10], encoding="utf-8")
            output_str[i]+=" "

        # add temps to output_str
        output_str[6]=str(current_temp1, encoding="utf-8")
        output_str[6]+=" "
        output_str[7]=str(current_temp2, encoding="utf-8")
        output_str[7]+=" "

        # add all info to grafana_str
        for i in range(8):
            grafana_str+=labels[i]
            grafana_str+=output_str[i]
            grafana_str+=str(current_time)
            grafana_str+="\n"

        os.system(grafana_str)
        sys.stdout.flush()
        time.sleep(1)

main()        

#if __name__ == "__main__":
#    main()
