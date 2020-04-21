#!/usr/bin/env python3
"""
Listens for connections from transmitters and saves ping output in DB.
"""
from writer import Writer

from websockets.server import WebSocketServerProtocol as Websocket
from typing import Optional
from queue import Queue
import configparser
import websockets
import argparse
import asyncio
import logging
import queue
import json
import sys

import misc



write_queue: Queue = None  # queue of messages that need to be recorded.
clients: dict = {}  # all connected clients, keyed on client name.


def read_config(filename: str) -> configparser.ConfigParser:
    parser = configparser.ConfigParser(allow_no_value=True)
    parser.read(filename)
    return parser


def handle_output_message(remote_addr: tuple, client_name: str, message: dict):
    global write_queue
    if 'id' not in message:
        logging.warning("Output message from %s has no id. Discarding.", remote_addr)
    message['remote_ip'] = remote_addr[0]
    message['prober_name'] = client_name
    write_queue.put(message)
    logging.debug("Enqueued message from %s. ID: %i", remote_addr, message['id'])
    return message['id']


def handle_auth_message(remote_addr: tuple, message: dict, websocket: Websocket) -> Optional[str]:
    global clients
    # right now, we don't actually do any authentication. we just register the client.
    name = message['name']
    if not name:
        logging.error("Blank name in auth message from %s", remote_addr)
        return None
    if name not in clients:
        clients[name] = websocket
        logging.info("Client from %s authenticated with name %s", remote_addr, name)
    else:
        logging.error("Client %s already registered. Duplicate name from %s", name, remote_addr)
        return None
    return name


def handle_client_disconnect(remote_addr: tuple, client_name: str) -> None:
    global clients
    try:
        clients.pop(client_name)
    except KeyError:
        logging.debug("Could not pop client %s named %s from clients list - not in list", remote_addr, client_name)


async def handle_client(websocket: websockets.server.WebSocketServerProtocol, request_uri) -> None:
    """ Coroutine handler for websocket connections from probers.

     :param websocket: The websocket connection from a newly connected client.
     :param request_uri: The path requested in the websocket HTTP request. Not currently used.
     :return: None
     """
    remote_addr = websocket.remote_address
    client_name: Optional[str] = None
    try:
        logging.info("New connection from %s:%s", remote_addr[0],
                     remote_addr[1])
        while True:
            message_string = await websocket.recv()
            try:
                message = json.loads(message_string)
                logging.debug("message from %s: %s", remote_addr[0], message)
            except ValueError:
                logging.error("Message from %s (%s) is not valid JSON", client_name, remote_addr)
                continue
            if 'type' not in message:
                logging.error("Message from %s (%s) has no type. Discarding.", client_name, remote_addr)
            elif message['type'] == 'auth':
                client_name = handle_auth_message(remote_addr, message, websocket)
            elif not client_name:
                logging.error("Received non-auth type message from un-authed client %s", remote_addr)
            elif message['type'] == 'output':
                message_id = handle_output_message(remote_addr, client_name, message)
                response = json.dumps({'type': 'output_ack', 'status': 'enqueued', 'id': message_id})
                await websocket.send(response)
            else:
                logging.error("Unknown message from %s type: %s", remote_addr, message['type'])
    except websockets.exceptions.ConnectionClosed as e:
        logging.info("Connection from %s:%s closed: %s", remote_addr[0],
                     remote_addr[1], str(e))
    finally:
        handle_client_disconnect(remote_addr, client_name)


def parse_args() -> argparse.Namespace:
    description = "Record ping results to some database."
    parser = misc.make_generic_parser(description)
    args = parser.parse_args()
    return args


def startup_checks(args):
    """ Checks the server should do before it is ready to go. """
    pass


def main():
    global write_queue
    args = parse_args()
    logger = logging.getLogger('websockets.server')
    logger.setLevel(logging.ERROR)
    logger.addHandler(logging.StreamHandler())
    config_parser = read_config(args.config_file)
    log_format = '%(asctime)s %(levelname)s:%(module)s:%(funcName)s# ' \
                 + '%(message)s'
    if args.foreground:
        logging.basicConfig(format=log_format, level=args.log_level)
    else:
        log_filename = config_parser['server']['log_file']
        logging.basicConfig(filename=log_filename, format=log_format,
                            level=args.log_level)
    logging.debug("Read config file: %s", args.config_file)
    server_config = config_parser['server']
    startup_checks(args)
    write_queue = queue.Queue()
    listen_ip = config_parser['server']['ws_address']
    listen_port = int(config_parser['server']['ws_port'])
    server = websockets.serve(handle_client, listen_ip, listen_port)
    logging.info("Started listening on %s:%s", listen_ip, str(listen_port))
    writer = Writer(write_queue, server_config)
    writer.start()
    asyncio.get_event_loop().run_until_complete(server)
    try:
        asyncio.get_event_loop().run_forever()
    except KeyboardInterrupt:
        logging.warning("Server shutting down.")
        writer.stop()


if __name__ == '__main__':
    main()
