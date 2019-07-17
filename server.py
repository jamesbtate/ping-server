#!/usr/bin/env python3
"""
Listens for connections from transmitters and saves ping output in DB.
"""
from writer import Writer
import configparser
import websockets
import argparse
import asyncio
import logging
import queue
import json


db_queue = None


def read_config():
    parser = configparser.ConfigParser(allow_no_value=True)
    parser.read('ping.conf')
    return parser


def handle_message_string(remote_addr, message_string):
    message = json.loads(message_string)
    logging.debug("message from %s: %s", remote_addr[0], message)
    if 'type' not in message:
        logging.warning("Message from %s has no type. Discarding.", remote_addr)
    elif 'id' not in message:
        logging.warning("Message from %s has no id. Discarding.", remote_addr)
    elif message['type'] == 'output':
        message['remote_ip'] = remote_addr[0]
        db_queue.put(message)
        logging.debug("Enqueued message from %s. ID: %i", remote_addr, message['id'])
        return message['id']
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
            message_id = handle_message_string(remote_addr, message_string)
            response = json.dumps({'status': 'enqueued', 'id': message_id})
            yield from websocket.send(response)
    except websockets.exceptions.ConnectionClosed as e:
        logging.info("Connection from %s:%s closed: %s", remote_addr[0],
                     remote_addr[1], str(e))


def parse_args():
    description = "Record ping results to some database."
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('-f', '--foreground', action='store_true',
                        help="Run in foreground and log to stderr.")
    args = parser.parse_args()
    return args


def main():
    global db_queue
    args = parse_args()
    logger = logging.getLogger('websockets.server')
    logger.setLevel(logging.ERROR)
    logger.addHandler(logging.StreamHandler())
    config_parser = read_config()
    log_format = '%(asctime)s %(levelname)s:%(module)s:%(funcName)s# ' \
                 + '%(message)s'
    log_level = logging.INFO
    if args.foreground:
        logging.basicConfig(format=log_format, level=log_level)
    else:
        log_filename = config_parser['server']['log_file']
        logging.basicConfig(filename=log_filename, format=log_format,
                            level=log_level)
    db_queue = queue.Queue()
    listen_ip = config_parser['server']['ws_address']
    listen_port = int(config_parser['server']['ws_port'])
    server = websockets.serve(listen, listen_ip, listen_port)
    logging.info("Started listening on %s:%s", listen_ip, str(listen_port))
    writer = Writer(db_queue, config_parser['server'])
    writer.start()
    asyncio.get_event_loop().run_until_complete(server)
    asyncio.get_event_loop().run_forever()


if __name__ == '__main__':
    main()
