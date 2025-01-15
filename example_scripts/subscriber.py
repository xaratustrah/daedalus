import zmq
import signal
import sys

output_file_path = 'received_data.txt'

context = zmq.Context()
socket = context.socket(zmq.SUB)
socket.connect("tcp://localhost:5556")
socket.setsockopt_string(zmq.SUBSCRIBE, "")

# Open the file for writing
file = open(output_file_path, 'w')

def signal_handler(sig, frame):
    print("\nTermination signal received. Closing file and exiting...")
    file.close()
    sys.exit(0)

# Register the signal handler
signal.signal(signal.SIGINT, signal_handler)

while True:
    try:
        message = socket.recv_string()
        file.write(message + '\n')
        file.flush()  # Ensure the data is written to file immediately
        print("Chunk received and saved")
    except KeyboardInterrupt:
        signal_handler(None, None)
