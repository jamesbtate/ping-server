#!/usr/bin/env python3
"""
Listens for connections from transmitters and saves ping output in DB.
"""


from websockets.server import WebSocketServerProtocol as Websocket
from asgiref.sync import sync_to_async
from typing import Optional
from queue import Queue
import websockets
import argparse
import asyncio
import logging
import queue
import json

import django_standalone  # need this. Don't delete because PyCharm thinks it is "unused"
from pingweb.models import Prober
from writer import Writer
import config
import misc


write_queue: Queue = None  # queue of messages that need to be recorded.
clients: dict = {}  # all connected clients, keyed on client name.


def handle_output_message(remote_addr: tuple, client_name: str, message: dict):
    global write_queue
    if 'id' not in message:
        logging.warning("Output message from %s has no id. Discarding.", remote_addr)
    message['remote_ip'] = remote_addr[0]
    message['prober_name'] = client_name
    write_queue.put(message)
    logging.debug("Enqueued message from %s. ID: %i", remote_addr, message['id'])
    return message['id']


@sync_to_async
def get_target_list(name: str) -> str:
    """ Gather the list of targets for this client and craft the message.

    Does nothing if client's name is not in the database.

    :return: The JSON-dumped string message to send to the client.
    """
    try:
        prober = Prober.objects.get(name=name)
    except Prober.DoesNotExist:
        logging.error(f"Cannot get targets for unknown prober {name}")
        return None
    targets = prober.get_unique_targets()
    target_dicts = []
    for target in targets:
        d = {
            'ip': target.ip,
            'type': target.type,
            'port': target.port,
        }
        target_dicts.append(d)
    message = json.dumps({'type': 'target_list', 'targets': target_dicts})
    return message


@sync_to_async
def get_prober_by_name(name: str):
    """ Wrapper to get Prober from Django ORM.

    Uses sync_to_async decorator because Django ORM is not async-compatible.

    :return: Prober object or None if no object exists.
    """
    try:
        prober = Prober.objects.get(name=name)
        return prober
    except Prober.DoesNotExist:
        return None


async def handle_auth_message(remote_addr: tuple, message: dict, websocket: Websocket) -> Optional[str]:
    global clients
    # right now, we don't actually do any authentication. we just register the client.
    name = message['name']
    if not name:
        logging.error("Blank name in auth message from %s. Disconnecting client", remote_addr)
        await websocket.close()
        return None
    if name not in clients:
        prober = await get_prober_by_name(name)
        if prober is None:
            logging.error(f"Connection from unknown prober name: {name}. Disconnecting client.")
            await websocket.close()
            return None
        clients[name] = websocket
        logging.info("Client from %s authenticated with name %s", remote_addr, name)
        message = await get_target_list(name)
        if message is None:
            logging.error(f"No targets for prober {name}. Disconnecting client.")
            await websocket.close()
            return None
        await websocket.send(message)
        logging.debug(f"Sent target list to client {name}")
    else:
        logging.error(f"Client {name} already registered. Duplicate name from {remote_addr}. Disconnecting client.")
        await websocket.close()
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
                client_name = await handle_auth_message(remote_addr, message, websocket)
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
    config.check_defaults_in_db()
    pass


def setup_logging(args):
    ws_logger = logging.getLogger('websockets.server')
    ws_logger.setLevel(logging.ERROR)
    ws_logger.addHandler(logging.StreamHandler())
    log_format = '%(asctime)s %(levelname)s:%(module)s:%(funcName)s# ' \
                 + '%(message)s'
    if args.foreground:
        handler = logging.StreamHandler()
    else:
        log_filename = config.get_setting_string('collector_log_file')
        handler = logging.FileHandler(log_filename)
    formatter = logging.Formatter(log_format)
    handler.setFormatter(formatter)
    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(args.log_level)
    logging.debug(f"Setup logging with level: {args.log_level}")


def main():
    global write_queue
    args = parse_args()
    setup_logging(args)
    startup_checks(args)
    write_queue = queue.Queue()
    listen_ip = config.get_setting_string('ws_address')
    listen_port = int(config.get_setting_string('ws_port'))
    server = websockets.serve(handle_client, listen_ip, listen_port)
    logging.info("Started listening on %s:%s", listen_ip, str(listen_port))
    writer = Writer(write_queue)
    writer.start()
    asyncio.get_event_loop().run_until_complete(server)
    try:
        asyncio.get_event_loop().run_forever()
    except KeyboardInterrupt:
        logging.warning("Server shutting down.")
        writer.stop()


if __name__ == '__main__':
    main()
