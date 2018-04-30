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
    logging.debug("message from %s: %s", remote_addr[0], message)
    if 'type' not in message:
        logging.warning("Message from %s has no type", remote_addr)
    elif message['type'] == 'output':
        message['remote_ip'] = remote_addr[0]
        db_queue.put(message)
    else:
        logging.warning("Unknown message from %s type: %s", remote_addr,
                        message['type'])


@asyncio.coroutine
def listen(websocket, path):
    remote_addr = websocket.remote_address
    try:
        logging.info("New connection from %s:%s", remote_addr[0],
                     remote_addr[1])
        while True:
            message_string = yield from websocket.recv()
            handle_message_string(remote_addr, message_string)
    except websockets.exceptions.ConnectionClosed as e:
        logging.info("Connection from %s:%s closed", remote_addr[0],
                     remote_addr[1])


if __name__ == '__main__':
    log_format = '%(asctime)s %(levelname)s:%(module)s:%(funcName)s ' \
                  + '%(message)s'
    logging.basicConfig(format=log_format, level=logging.INFO)
    parser = configparser.ConfigParser(allow_no_value=True)
    parser.read('ping.conf')
    db_queue = queue.Queue()
    listen_ip = parser['server']['ws_address']
    listen_port = int(parser['server']['ws_port'])
    server = websockets.serve(listen, listen_ip, listen_port)
    logging.info("Started listening on %s:%s", listen_ip, str(listen_port))
    writer = Writer(db_queue, parser['server'])
    writer.start()
    asyncio.get_event_loop().run_until_complete(server)
    asyncio.get_event_loop().run_forever()
