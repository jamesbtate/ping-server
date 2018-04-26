#!/usr/bin/python3
import threading
# import argparse
# import requests
import queue
# import time

from collector import Ping
from transmitter import Transmitter


output_queue = None


def enqueue_output(data):
    """ Accepts a dictionary containg send_time and replies[] """
    output_queue.put(data)
    print("enqueued output")


def dequeue_output():
    """ Pops a dictionary from the output queue """
    return output_queue.get()


def collector_run():
    hosts = ('192.168.5.5', '192.168.5.18', '8.8.8.8', 'ucla.edu')
    pinger = Ping(hosts, enqueue_output)
    pinger.run()


if __name__ == '__main__':
    output_queue = queue.Queue()
    collector_thread = threading.Thread(target=collector_run, name="collector")
    recorder_url = 'ws://localhost:8765/'
    transmitter = Transmitter(dequeue_output, recorder_url)
    collector_thread.start()
    transmitter.start()
