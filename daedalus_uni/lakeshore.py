"""
Daedalus project Lakeshore class

May 2025 xaratustrah@github

"""

import socket
import re
import time

class Lakeshore:
    def __init__(self, host, port, timeout=1):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.sock = None

    def connect(self):
        if self.sock is None:
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.settimeout(self.timeout)
                self.sock.connect((self.host, self.port))
            except socket.error as e:
                logger.error(f"Connection error: {e}")
                self.sock = None

    def get_temperature(self, message):
        message = message if message.endswith("\n") else message + "\n" # Ensure newline for proper request termination

        if not self.sock:
            self.connect()

        temp = 0
        try:
            self.sock.sendall(message.encode())
            response = self.sock.recv(1024).decode()

            if not response:
                raise ValueError("No incoming data")

            temp = float(re.sub(r'[^0-9.]', '', response))
            #time.sleep(1)  # Simulate nc -q 1 behavior

        except (socket.timeout, socket.error, ValueError) as e:
            raise # rethrow the exception
            
        return temp

    def close(self):
        if self.sock:
            self.sock.close()
            self.sock = None

