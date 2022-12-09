import socket
import json
from scanner.Dataclasses.Request import Request
from scanner.Dataclasses.Response import Response

HOST = "127.0.0.1"  # Standard loopback interface address (localhost)
PORT = 6000  # Port to listen on (non-privileged ports are > 1023)

def listen():
    print("Starting new session")

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((HOST, PORT))
    s.listen()
    conn, addr = s.accept()
    with conn:
        print(f"Connected by {addr}")
        data = bytearray()
        while True:
            chunk = conn.recv(1024)
            data = data + chunk
            if not chunk:
                break
        json_data = json.loads(data.decode('utf-8'))
        request = Request.from_dict(json_data['request'])
        response = Response.from_dict(json_data['response'])
        print(response.code)

while True:
    listen()
