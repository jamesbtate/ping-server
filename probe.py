#!/usr/bin/env python3
"""
Pings multiple hosts and forwards the results to a websocket server.

Largely based on pyping.py from
    https://github.com/Akhavi/pyping/blob/master/pyping/core.py

Note that ICMP messages can only be sent from processes running as root

GNU GPL v2 license  -  see LICENSE
"""
from websockets.client import WebSocketClientProtocol as WebSocket
from asyncio import Queue as AQueue
from queue import Queue as TQueue
import configparser
import websockets
import threading
import argparse
import asyncio
import logging
import random
import select
import signal
import socket
import struct
import queue
import json
import time
import sys
import os

# ICMP parameters
ICMP_ECHOREPLY = 0  # Echo reply (per RFC792)
ICMP_ECHO = 8  # Echo request (per RFC792)
ICMP_MAX_RECV = 2048  # Max size of incoming buffer
MAX_SLEEP = 1000
MESSAGE_ACK_TIMEOUT = 5.0  # how long to wait (seconds) before re-queueing a message to transmit

results_queue = None
event_loop = None
keep_going = True


class Pinger(object):
    """ A wrapper class for a thread that pings hosts and adds results to a queue.

    Uses raw IP sockets so it requires root (or some other convoluted privileges).
    """

    def __init__(self, destinations, timeout=500, packet_size=55,
                 output=sys.stdout, own_id=None, sourceaddress=False):
        logging.debug("Initialized Pinger. timeout: %i", timeout)
        self.destinations = [socket.gethostbyname(_) for _ in destinations]
        self.output = output
        self.timeout = timeout
        self.packet_size = packet_size
        if sourceaddress is not False:
            self.sourceaddress = socket.gethostbyname(sourceaddress)
        if own_id is None:
            self.own_id = os.getpid() & 0xFFFF  # just the 2 low-order bytes
        else:
            self.own_id = own_id

        self.seq_number = 0
        self.send_count = 0
        self.receive_count = 0

    def calculate_checksum(self, source_string):
        """
        A port of the functionality of in_cksum() from ping.c
        Ideally this would act on the string as a series of 16-bit ints (host
        packed), but this works.
        Network data is big-endian, hosts are typically little-endian
        """
        countTo = (int(len(source_string) / 2)) * 2
        sum = 0
        count = 0

        # Handle bytes in pairs (decoding as short ints)
        loByte = 0
        hiByte = 0
        while count < countTo:
            if (sys.byteorder == "little"):
                loByte = source_string[count]
                hiByte = source_string[count + 1]
            else:
                loByte = source_string[count + 1]
                hiByte = source_string[count]
            sum = sum + (hiByte * 256 + loByte)
            count += 2

        # Handle last byte if applicable (odd-number of bytes)
        # Endianness should be irrelevant in this case
        if countTo < len(source_string):  # Check for odd length
            loByte = source_string[len(source_string) - 1]
            sum += loByte

        sum &= 0xffffffff  # Truncate sum to 32 bits (a variance from ping.c)

        sum = (sum >> 16) + (sum & 0xffff)  # Add high 16 bits to low 16 bits
        sum += (sum >> 16)  # Add carry from above (if any)
        answer = ~sum & 0xffff  # Invert and truncate to 16 bits
        answer = socket.htons(answer)

        return answer

    def header2dict(self, names, struct_format, data):
        """
        unpack the raw received IP and ICMP header informations to a dict
        """
        unpacked_data = struct.unpack(struct_format, data)
        return dict(zip(names, unpacked_data))

    def make_raw_socket(self):
        try:  # One could use UDP here, but it's obscure
            current_socket = socket.socket(socket.AF_INET, socket.SOCK_RAW,
                                           socket.getprotobyname("icmp"))
            logging.info("Made raw socket")
            return current_socket
        except socket.error as e:
            if e.errno == 1:
                # Operation not permitted - Add more information to traceback
                logging.error("Error making raw socket")
                etype, evalue, etb = sys.exc_info()
                evalue = etype(
                    """%s - Note that ICMP messages can only be sent
                    from processes running as root.""" % evalue
                )
                # raise etype, evalue, etb
                raise evalue
            raise  # raise the original error

    def run(self):
        """ send and receive pings """
        global keep_going
        start_time = time.time()
        iteration = 0
        try:
            current_socket = self.make_raw_socket()
        except PermissionError:
            logging.critical("Need root to make a raw socket. Shutting down...")
            keep_going = False

        while keep_going:
            logging.debug("Inside main loop")
            iteration += 1
            send_time = time.time()
            for destination in self.destinations:
                self.send_one_ping(current_socket, destination)

            replies = self.receive_pings(current_socket, self.destinations)
            self.handle_output(send_time, replies)

            self.seq_number += 1
            if self.seq_number > 65535:
                self.seq_number -= 65536

            # Pause for the remainder of the MAX_SLEEP period (if applicable)
            time_left = start_time + iteration - time.time()
            if time_left > 0:
                time.sleep(time_left)
            else:
                msg = "Warning: iteration took longer than one second {:.2f}"
                msg = msg.format(time_left * -1 + 1)
                logging.warning(msg)
        logging.info("Exited ping loop in Pinger:run()")

    def send_one_ping(self, current_socket, destination):
        """
        Send one ICMP ECHO_REQUEST
        """
        # Header is type (8), code (8), checksum (16), id (16), sequence (16)
        checksum = 0
        # Make a dummy header with a 0 checksum.
        header = struct.pack(
            "!BBHHH", ICMP_ECHO, 0, checksum, self.own_id, self.seq_number
        )
        padBytes = []
        startVal = 0x42
        for i in range(startVal, startVal + (self.packet_size)):
            padBytes += [(i & 0xff)]  # Keep chars in the 0-255 range
        data = bytes(padBytes)

        # Calculate the checksum on the data and the dummy header.
        # Checksum is in network order
        checksum = self.calculate_checksum(header + data)
        # Now that we have the right checksum, we put that in. It's just easier
        # to make up a new header than to stuff it into the dummy.
        header = struct.pack(
            "!BBHHH", ICMP_ECHO, 0, checksum, self.own_id, self.seq_number
        )

        packet = header + data

        try:
            # Port number is irrelevant for ICMP
            current_socket.sendto(packet, (destination, 1))
            logging.debug("Sent packet to %s", destination)
        except socket.error as e:
            logging.error("General failure (%s)" % (e.args[1]))
            return
        self.send_count += 1

    def receive_pings(self, current_socket, destinations):
        # receive_time, packet_size, ip, ip_header, icmp_header =
            # self.receive_one_ping(current_socket, destination)
        max_time = self.timeout / 1000.0
        timeout = max_time
        start_time = time.time()
        destinations_remaining = destinations[:]
        replies = []
        # print("receiving pings with seq_number", self.seq_number)
        while True:
            # call select() until we have received all pings or we time out
            logging.debug("Calling select() to receive ping response with timeout: %f", timeout)
            inputready, outputready, exceptready = \
                select.select([current_socket], [], [], timeout)
            if inputready == []:  # do not refactor this to "inputready is []"
                # timeout
                logging.debug("select() timed out")
                break
            receive_time = time.time()
            packet_data, address = current_socket.recvfrom(ICMP_MAX_RECV)
            logging.debug("Received packet from %s", address)
            # print("packet from", address[0])
            if address[0] in destinations_remaining:
                icmp_header = self.header2dict(
                    names=[
                        "type", "code", "checksum",
                        "packet_id", "seq_number"
                    ],
                    struct_format="!BBHHH",
                    data=packet_data[20:28]
                )

                # print("receiving packet from", address[0],
                #       "with seq_number", icmp_header["seq_number"],
                #       "and own_id", icmp_header["packet_id"])
                if icmp_header["packet_id"] == self.own_id and \
                        icmp_header["seq_number"] == self.seq_number:
                    # This is one of our packets
                    ip_header = self.header2dict(
                        names=[
                            "version", "type", "length",
                            "id", "flags", "ttl", "protocol",
                            "checksum", "src_ip", "dest_ip"
                        ],
                        struct_format="!BBHHHBBHII",
                        data=packet_data[:20]
                    )
                    ip = socket.inet_ntoa(struct.pack("!I",
                                          ip_header["src_ip"]))
                    replies.append((ip, receive_time))
                    destinations_remaining.remove(ip)
                else:
                    logging.debug("Received ICMP message from valid "
                                  "destination with invalid header.")
            else:
                logging.debug("Received ICMP packet from unexpected IP: %s", address[0])
            timeout = max_time - (time.time() - start_time)
            if timeout <= 0 or len(destinations_remaining) == 0:
                break
        for ip in destinations_remaining:
            replies.append((ip, None))
        logging.debug("Returning %i replies", len(replies))
        return replies

    def handle_output(self, send_time, replies):
        if self.output == sys.stdout:
            self.print_output(send_time, replies)
        else:
            data = {'type': 'output', 'send_time': send_time,
                    'replies': replies}
            self.output.put(data)

    def print_output(self, send_time, replies):
        if len(replies) == 0:
            print("No replies")
        for reply in replies:
            if reply[1] is None:
                print("no reply from {0}".format(reply[0]))
            else:
                millis = (reply[1] - send_time) * 1000
                print("reply from {0} in {1:.1f} ms".format(reply[0], millis))


def ping(timeout=500, packet_size=55, *args, **kwargs):
    hosts = ('192.168.5.5', '192.168.5.18', '8.8.8.8', 'ucla.edu')
    p = Pinger(hosts, timeout, packet_size, *args, **kwargs)
    p.run()


def _ping(hosts, output):
    p = Pinger(hosts, output=output)
    p.run()


async def maintain_collector_connection(config: configparser.SectionProxy,
                                        results_queue: TQueue,
                                        unconfirmed_list: list):
    """ Coroutine to connect to collector and re-connect if connection fails.

    Starts the other coroutines and restarts them if they stop.

    :param config: SectionProxy configuration section from config file
    :param results_queue: thread-safe queue of messages to transmit
    :param unconfirmed_list: a list of unconfirmed transmitted messages
    :return: None
    """
    global keep_going
    url = config['ws_url']
    transmit_task = None
    receive_task = None
    requeue_task = None
    while keep_going:
        logging.info("Connecting to websocket: %s", url)
        try:
            websocket = await websockets.connect(url)
            logging.debug("Connected to websocket %s", url)
            auth_message = {'type': 'auth', 'name': config['name']}
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
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('-c', '--config-file', default='ping.conf',
                        help="Path to config file. Default is ./ping.conf")
    parser.add_argument('-f', '--foreground', action='store_true',
                        help="Run in foreground and log to stderr.")
    parser.add_argument('-d', '--debug', dest='log_level',
                        default=logging.INFO, action='store_const',
                        const=logging.DEBUG,
                        help="Enable debug-level logging.")
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
    args = parse_args()
    log_format = '%(asctime)s %(levelname)s:%(module)s:%(funcName)s# ' \
                 + '%(message)s'
    config_parser = configparser.ConfigParser(allow_no_value=True)
    config_parser.read(args.config_file)
    probe_config = config_parser['probe']
    if args.foreground:
        logging.basicConfig(format=log_format, level=args.log_level)
    else:
        log_filename = probe_config['log_file']
        logging.basicConfig(filename=log_filename, format=log_format,
                            level=args.log_level)
    logging.debug("Read config file: %s", args.config_file)
    setup_signal_handler()
    results_queue = TQueue()
    unconfirmed_list = []
    hosts = ping_targets_from_config(config_parser)
    args = (hosts, results_queue)
    ping_thread = threading.Thread(target=_ping, args=args)
    logging.info("Starting ping thread")
    ping_thread.start()
    logging.info("Starting event loop")
    event_loop = asyncio.get_event_loop()
    main_task = maintain_collector_connection(probe_config, results_queue, unconfirmed_list)
    try:
        event_loop.run_until_complete(main_task)
    except KeyboardInterrupt:
        logging.debug("Caught KeyboardInterrupt in main()")
        shutdown()


if __name__ == '__main__':
    main()
