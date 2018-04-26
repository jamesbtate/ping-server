#!/usr/bin/python3
"""
Transmits ping output to the recorder.
"""
import websockets
import threading
import asyncio
import json
import time


class Transmitter(threading.Thread):
    def __init__(self, read_message, recorder_url):
        """ Arguments:
        read_message - a function that returns one ouput dict
        recorder - URL to the websocket recorder
        """
        threading.Thread.__init__(self)
        self.read_message = read_message
        self.recorder_url = recorder_url
        # self.thread = threading.Thread(target=self.run, name="transmitter")
        self.keep_going = True
        self.websocket = None
        print("Initialized transmitter")

    """
    def start(self):
        print("starting transmitter")
        self.thread.start()
    """

    def stop(self):
        self.keep_going = False

    @asyncio.coroutine
    def connect(self):
        self.websocket = yield from websockets.connect(self.recorder_url)

    @asyncio.coroutine
    def run(self):
        print("started transmitter")
        while self.keep_going:
            yield from self.connect()
            print("connected to websocket", self.websocket.remote_address)
            while self.keep_going:
                message = self.read_message()
                yield from self.websocket.send(json.dumps(message))
                time.sleep(1)


"""
@asyncio.coroutine
def send_messages():
    websocket = yield from websockets.connect('ws://localhost:8765/')

    try:
        while True:
            name = input("Message? ")
            yield from websocket.send(name)
    finally:
        yield from websocket.close()


asyncio.get_event_loop().run_until_complete(send_messages())
"""
