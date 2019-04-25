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

    def src_dst_id(self, src, dst):
        """ Gets the ID of the src-dst pair from the DB, maybe creating the entry.
        Create a new src-dst pair in the DB if it does not already exist.
        Returns the ID of src-dst pair. """
        query = "SELECT id FROM src_dst WHERE src=INET_ATON(%s) \
                 AND dst=INET_ATON(%s)"
        params = (src, dst)
        self.db.cursor.execute(query, params)
        result = self.db.cursor.fetchone()
        if not result:
            # we need to create the src-dst pair
            query = "INSERT INTO src_dst (src,dst) VALUES \
                     (INET_ATON(%s),INET_ATON(%s))"
            self.db.cursor.execute(query, params)
            self.db.connection.commit()
            return self.db.cursor.lastrowid
        return result['id']

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
            if receive_time is None:
                short_latency = 65535  # magic value in the not null column
            else:
                latency = receive_time - send_time  # in seconds
                if latency > 1:
                    short_latency = 65535  # treat >1000ms replies as timeouts
                else:
                    short_latency = round(latency * 65534)  # int in 0..65534
            src_dst_id = self.src_dst_id(remote_ip, target)
            send_datetime = datetime.datetime.fromtimestamp(send_time)
            query = "INSERT INTO output (time, src_dst, latency) \
                     VALUES (%s, %s, %s)"
            params = (send_datetime, src_dst_id, short_latency)
            self.db.cursor.execute(query, params)
            self.db.connection.commit()

    def run(self):
        logging.info("Started DB writer")
        while self.keep_going:
            try:
                message = self.db_queue.get(timeout=0.5)
            except queue.Empty as e:
                continue
            logging.debug("writerqueued message for writing")
            self.store_output(message)
