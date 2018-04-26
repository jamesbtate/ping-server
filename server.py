#!/usr/bin/python3
"""
Listens for connections from transmitters and saves ping ouput in DB.
"""
from writer import Writer
import configparser
import websockets
import asyncio
import logging
import queue
import json


logger = logging.getLogger('websockets.server')
logger.setLevel(logging.ERROR)
logger.addHandler(logging.StreamHandler())
db_queue = None


def handle_message_string(remote_addr, message_string):
    message = json.loads(message_string)
    print(remote_addr[0], message)
    if 'type' not in message:
        print("Message from", remote_addr, "has no type")
    elif message['type'] == 'output':
        db_queue.put(message)
    else:
        print("Unknown message from", remote_addr, "type:", message['type'])


@asyncio.coroutine
def listen(websocket, path):
    remote_addr = websocket.remote_address
    try:
        print("New connection from", remote_addr[0], remote_addr[1])
        while True:
            message_string = yield from websocket.recv()
            handle_message_string(remote_addr, message_string)
    except websockets.exceptions.ConnectionClosed as e:
        print("Connection from", remote_addr[0], remote_addr[1], "closed")


if __name__ == '__main__':
    parser = configparser.ConfigParser()
    parser.read('ping.conf')
    db_queue = queue.Queue()
    server = websockets.serve(listen, 'localhost', 8765)
    writer = Writer(db_queue, parser['server'])
    writer.start()
    asyncio.get_event_loop().run_until_complete(server)
    asyncio.get_event_loop().run_forever()
