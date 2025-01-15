import zmq
import random
import time

context = zmq.Context()
socket = context.socket(zmq.PUB)
socket.bind("tcp://localhost:5556")

while True:
    chunk = [random.randint(0, 100) for _ in range(1024)]
    message = ' '.join(map(str, chunk))
    socket.send_string(message)
    print("Chunk sent")
    time.sleep(1)  # Adjust sleep time as needed
