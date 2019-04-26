"""
Contains Thread subclass for writing to DB
"""
import mysql.connector
import threading
import datetime
import logging
import queue
from database_mysql import DatabaseMysql


class Writer(threading.Thread):
    def __init__(self, db_queue, db_params):
        threading.Thread.__init__(self)
        self.db_queue = db_queue
        self.db = DatabaseMysql(db_params)
        self.keep_going = True

    def stop(self):
        self.keep_going = False

    def store_output(self, message):
        """ Stores the ping results in the database

            message: {'send_time': 1234567890.1,
                      'remote_ip': '1.2.3.4',
                      'replies': [
                       ('5.6.7.8', 1234567890.2)
                      ]
                     }
        """
        send_time = message['send_time']
        remote_ip = message['remote_ip']
        for reply in message['replies']:
            target = reply[0]
            receive_time = reply[1]
            self.db.record_poll_data(remote_ip, target, send_time, receive_time)

    def run(self):
        logging.info("Started DB writer")
        while self.keep_going:
            try:
                message = self.db_queue.get(timeout=0.5)
            except queue.Empty as e:
                continue
            logging.debug("writer queued message for writing")
            self.store_output(message)
