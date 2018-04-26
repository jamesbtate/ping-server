"""
Contains Thread subclass for writing to DB
"""
import mysql.connector
import threading
import queue


class Writer(threading.Thread):
    def __init__(self, db_queue, db_params):
        threading.Thread.__init__(self)
        self.db_queue = db_queue
        self.db_params = db_params
        self.keep_going = True
        self.connection = None
        self.cursor = None

    def stop(self):
        self.keep_going = False

    def _connect_db(self):
        c = mysql.connector.connect(user=self.db_params['db_user'],
                                    password=self.db_params['db_pass'],
                                    host=self.db_params['db_host'],
                                    database=self.db_params['db_db'])
        self.connection = c
        self.cursor = self.connection.cursor()

    def store_output(self, message):
        todo = 1

    def run(self):
        print("Started DB writer")
        self._connect_db()
        while self.keep_going:
            try:
                message = self.db_queue.get(timeout=0.5)
            except queue.Empty as e:
                continue
            print("queued message for writing")
            self.store_output(message)
