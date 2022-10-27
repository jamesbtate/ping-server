#!/usr/bin/env python3
"""
Pings multiple hosts and forwards the results to a websocket server.

Largely based on pyping.py from
    https://github.com/Akhavi/pyping/blob/master/pyping/core.py

Note that ICMP messages can only be sent from processes running as root

GNU GPL v2 license  -  see LICENSE
"""
from websockets.client import WebSocketClientProtocol as WebSocket
from queue import Queue as TQueue
import websockets
import asyncio
import logging
import random
import signal
import socket
import queue
import json
import time

from pinger import Pinger
import misc
import env

MAX_SLEEP = 1000
MESSAGE_ACK_TIMEOUT = 5.0  # how long to wait (seconds) before re-queueing a message to transmit

results_queue = None
event_loop = None
keep_going = True
pinger: Pinger = None




def ping(timeout=500, packet_size=55, *args, **kwargs):
    hosts = ('192.168.5.5', '192.168.5.18', '8.8.8.8', 'ucla.edu')
    p = Pinger(hosts, timeout, packet_size, *args, **kwargs)
    p.run()


async def maintain_collector_connection(results_queue: TQueue,
                                        unconfirmed_list: list):
    """ Coroutine to connect to collector and re-connect if connection fails.

    Starts the other coroutines and restarts them if they stop.

    :param results_queue: thread-safe queue of messages to transmit
    :param unconfirmed_list: a list of unconfirmed transmitted messages
    :return: None
    """
    global keep_going
    url = env.get_env_string('PROBER_WS_URL')
    name = env.get_env_string('PROBER_NAME')
    transmit_task = None
    receive_task = None
    requeue_task = None
    while keep_going:
        logging.info("Connecting to websocket: %s", url)
        try:
            websocket = await websockets.connect(url)
            logging.debug("Connected to websocket %s", url)
            auth_message = {'type': 'auth', 'name': name, }
            await websocket.send(json.dumps(auth_message))
        except OSError as e:
            logging.error("Error connecting to websocket: %s", str(e))
            await asyncio.sleep(1)
            continue
        while keep_going and websocket.open:
            if transmit_task is None or transmit_task.done():
                transmit_task = asyncio.ensure_future(transmit_results(results_queue, websocket, unconfirmed_list))
            if receive_task is None or receive_task.done():
                receive_task = asyncio.ensure_future(receive_messages(websocket, unconfirmed_list))
            if requeue_task is None or requeue_task.done():
                requeue_task = asyncio.ensure_future(requeue_stale_messages(unconfirmed_list, results_queue))
            await asyncio.sleep(1)
        logging.info("websocket died or keep_going is False")
    logging.info("keep_going is False in maintain_collector_connection()")


async def transmit_results(results_queue: TQueue, websocket: WebSocket, unconfirmed_list: list):
    """ Coroutine to send ping results to collector (server) over a websocket.

    JSON-dumps items from the queue and sends them over the websocket. Adds
    each sent item to the unconfirmed_queue for some other task to verify.

    :param results_queue: thread-safe queue of messages to transmit
    :param websocket: already connected websocket from websockets package
    :param unconfirmed_list: a list of unconfirmed transmitted messages
    :return: None
    """
    global keep_going
    nonce = random.randint(0, 2 ** 40)
    while keep_going:
        try:
            data = results_queue.get(block=False)
            logging.debug("Read data from output queue")
        except queue.Empty:
            await asyncio.sleep(1.0)
            continue
        data['id'] = nonce
        data['message_transmit_time'] = time.time()
        nonce += 1
        await websocket.send(json.dumps(data))
        unconfirmed_list.append(data)


def handle_target_list(message: dict):
    """ Update the target list with the list from the target_list message. """
    global pinger
    target_dicts = message['targets']
    target_ips = [_['ip'] for _ in target_dicts]
    # this is where we would do something complicated if we supported more than ICMP echo.
    pinger.set_destinations(target_ips)
    logging.info("Updated target list with %s targets", len(target_ips))


async def receive_messages(websocket: WebSocket, unconfirmed_list: list):
    """ Coroutine to receive any messages from collector and send to handlers.

    :param websocket: already connected websocket from websockets package
    :param unconfirmed_list: a list of unconfirmed transmitted messages
    :return: None
    """
    global keep_going
    while keep_going:
        message_string = await websocket.recv()
        message = json.loads(message_string)
        try:
            if message['type'] == 'output_ack':
                # this magic removes any messages in unconfirmed_list that have the same id
                #  as the acknowledgement message we just received.
                old_len = len(unconfirmed_list)
                unconfirmed_list[:] = [_ for _ in unconfirmed_list if message['id'] != _['id']]
                new_len = len(unconfirmed_list)
                logging.debug("Confirmed %i messages in unconfirmed_list", old_len - new_len)
            elif message['type'] == 'target_list':
                handle_target_list(message)
            else:
                logging.error("Unknown websocket message type received: %s", message_string)
        except KeyError:
            logging.error("received websocket message without type: %s", message_string)


async def requeue_stale_messages(unconfirmed_list: list, results_queue: TQueue):
    """ Re-queue messages in unconfirmed_list if they are not acknowledged.

     Waits MESSAGE_ACK_TIMEOUT seconds before re-queueing.

    :param unconfirmed_list: a list of unconfirmed transmitted messages
    :param results_queue: thread-safe queue of messages to transmit
    :return:
    """
    global keep_going
    while keep_going:
        stale_cutoff_time = time.time() - MESSAGE_ACK_TIMEOUT
        await asyncio.sleep(1.0)
        # it is critical that these two list comprehensions have opposite filters
        stale_messages = [_ for _ in unconfirmed_list if _['message_transmit_time'] < stale_cutoff_time]
        unconfirmed_list[:] = [_ for _ in unconfirmed_list if _['message_transmit_time'] >= stale_cutoff_time]
        for message in stale_messages:
            if stale_cutoff_time > message['message_transmit_time']:
                logging.info("Re-enqueueing data that was not acknowledged. id: %s", message['id'])
                results_queue.put(message)


def signal_handler(signum, frame):
    """ Handle exit via signals """
    msg = "(Terminated with signal %d)" % signum
    logging.error(msg)
    shutdown()


def shutdown():
    logging.debug("Shutting down...")
    global keep_going
    global event_loop
    keep_going = False
    pinger.stop()
    sleep_time = 2
    logging.warning("Stopping event loop in %i seconds", sleep_time)
    time.sleep(sleep_time)
    event_loop.stop()
    logging.warning("Probe shutting down with %i messages in transmit queue.",
                    results_queue.qsize())
    # sys.exit(0)


def setup_signal_handler():
    signal.signal(signal.SIGINT, signal_handler)   # Handle Ctrl-C
    signal.signal(signal.SIGTERM, signal_handler)  # Handle container stop
    if hasattr(signal, "SIGBREAK"):
        # Handle Ctrl-Break e.g. under Windows
        signal.signal(signal.SIGBREAK, signal_handler)


def parse_args():
    description = "Ping stuff and send the responses to a recording server."
    parser = misc.make_generic_parser(description)
    args = parser.parse_args()
    return args


def ping_targets_from_config(config):
    """ Read the ping targets from the config parser. Returns a list of IPs"""
    section = config['probe targets']
    addresses = []
    for key in section.keys():
        try:
            addr = socket.gethostbyname(key)
            logging.debug("Resolved probe target: %s => %s", key, addr)
            addresses.append(addr)
        except socket.gaierror:
            logging.error("Unable to resolve probe target: %s", key)
    return addresses


def main():
    global results_queue
    global event_loop
    global pinger
    args = parse_args()
    log_format = '%(asctime)s %(levelname)s:%(module)s:%(funcName)s# ' \
                 + '%(message)s'
    if args.foreground:
        logging.basicConfig(format=log_format, level=args.log_level)
    else:
        log_filename = env.get_env_string('PROBER_LOG_FILE')
        logging.basicConfig(filename=log_filename, format=log_format,
                            level=args.log_level)
    setup_signal_handler()
    results_queue = TQueue()
    unconfirmed_list = []
    hosts = []
    logging.info("Starting ping thread")
    pinger = Pinger(hosts, output=results_queue)
    pinger.start()
    logging.info("Starting event loop")
    event_loop = asyncio.get_event_loop()
    main_task = maintain_collector_connection(results_queue, unconfirmed_list)
    try:
        event_loop.run_until_complete(main_task)
    except KeyboardInterrupt:
        logging.debug("Caught KeyboardInterrupt in main()")
        shutdown()


if __name__ == '__main__':
    main()
