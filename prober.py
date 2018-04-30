#!/usr/bin/python3
"""
Pings multiple hosts and forwards the results to a websocket server.

Largely based on pyping.py from
    https://github.com/Akhavi/pyping/blob/master/pyping/core.py

Note that ICMP messages can only be sent from processes running as root

GNU GPL v2 license  -  see LICENSE
"""

import configparser
import websockets
import threading
import asyncio
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

output_queue = None
keep_going = True


def calculate_checksum(source_string):
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

    sum &= 0xffffffff   # Truncate sum to 32 bits (a variance from ping.c)

    sum = (sum >> 16) + (sum & 0xffff)    # Add high 16 bits to low 16 bits
    sum += (sum >> 16)                    # Add carry from above (if any)
    answer = ~sum & 0xffff                # Invert and truncate to 16 bits
    answer = socket.htons(answer)

    return answer


def is_valid_ipv4_address(addr):
    parts = addr.split(".")
    if not len(parts) == 4:
        return False
    for part in parts:
        try:
            number = int(part)
        except ValueError:
            return False
        if number > 255 or number < 0:
            return False
    return True


def to_ip(addr):
    if is_valid_ipv4_address(addr):
        return addr
    return socket.gethostbyname(addr)


class Pinger(object):
    def __init__(self, destinations,  timeout=500, packet_size=55,
                 output=sys.stdout, own_id=None, sourceaddress=False):
        self.destinations = [socket.gethostbyname(_) for _ in destinations]
        self.output = output
        self.timeout = timeout
        self.packet_size = packet_size
        if sourceaddress is not False:
            self.sourceaddress = socket.gethostbyname(sourceaddress)
        if own_id is None:
            self.own_id = os.getpid() & 0xFFFF
        else:
            self.own_id = own_id

        self.seq_number = 0
        self.send_count = 0
        self.receive_count = 0

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
            return current_socket
        except socket.error as e:
            if e.errno == 1:
                # Operation not permitted - Add more information to traceback
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
        # self.setup_signal_handler()
        start_time = time.time()
        iteration = 0
        current_socket = self.make_raw_socket()

        while keep_going:
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
            if (time_left > 0):
                time.sleep(time_left)
            else:
                msg = "Warning: iteration took longer than one second {:.2f}"
                msg = msg.format(time_left * -1 + 1)
                print(msg)

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
        checksum = calculate_checksum(header + data)
        # Now that we have the right checksum, we put that in. It's just easier
        # to make up a new header than to stuff it into the dummy.
        header = struct.pack(
            "!BBHHH", ICMP_ECHO, 0, checksum, self.own_id, self.seq_number
        )

        packet = header + data

        try:
            # Port number is irrelevant for ICMP
            current_socket.sendto(packet, (destination, 1))
        except socket.error as e:
            print("General failure (%s)" % (e.args[1]))
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
            inputready, outputready, exceptready = \
                select.select([current_socket], [], [], timeout)
            if inputready == []:  # timeout
                break
            receive_time = time.time()

            packet_data, address = current_socket.recvfrom(ICMP_MAX_RECV)
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

            timeout = max_time - (time.time() - start_time)
            if timeout <= 0 or len(destinations_remaining) == 0:
                break
        for ip in destinations_remaining:
            replies.append((ip, None))
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


@asyncio.coroutine
def transmit_loop():
    while keep_going:
        url = 'ws://localhost:8765/'
        print("Connecting to websocket:", url)
        websocket = yield from websockets.connect(url)
        try:
            while keep_going:
                try:
                    data = output_queue.get(timeout=0.5)
                except queue.Empty as e:
                    continue
                yield from websocket.send(json.dumps(data))
        except Exception as e:
            print("Exception in transmit loop:", str(e))


def signal_handler(signum, frame):
    """ Handle exit via signals """
    global keep_going
    msg = "\n(Terminated with signal %d)\n" % (signum)
    print(msg)
    keep_going = False
    event_loop.stop()
    # sys.exit(0)


def setup_signal_handler():
    signal.signal(signal.SIGINT, signal_handler)   # Handle Ctrl-C
    if hasattr(signal, "SIGBREAK"):
        # Handle Ctrl-Break e.g. under Windows
        signal.signal(signal.SIGBREAK, signal_handler)


if __name__ == '__main__':
    parser = configparser.ConfigParser(allow_no_value=True)
    parser.read('ping.conf')
    setup_signal_handler()
    output_queue = queue.Queue()
    event_loop = asyncio.get_event_loop()
    # ping(('192.168.5.5', '192.168.5.18', '8.8.8.8', 'ucla.edu'))
    hosts = ('192.168.5.5', '192.168.5.18', '8.8.8.8', 'ucla.edu', '1.2.3.4')
    args = (hosts, output_queue)
    ping_thread = threading.Thread(target=_ping, args=args)
    print("Starting ping thread")
    ping_thread.start()
    print("Starting event loop")
    # asyncio.get_event_loop().run_until_complete(transmit_loop())
    event_loop.create_task(transmit_loop())
    event_loop.run_forever()
