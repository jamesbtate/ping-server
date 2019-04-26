#!/usr/bin/python3
"""
Database abstraction layer
"""

import mysql.connector
import datetime
import time

from database import Database


class DatabaseMysql(Database):
    def __init__(self, db_params):
        self.connection = None
        self.cursor = None
        super().__init__()
        self.db_params = db_params
        self._connect_db()
        self.src_dst_pairs = {}

    def _connect_db(self):
        c = mysql.connector.connect(user=self.db_params['db_user'],
                                    password=self.db_params['db_pass'],
                                    host=self.db_params['db_host'],
                                    database=self.db_params['db_db'])
        self.connection = c
        self.cursor = self.connection.cursor(dictionary=True)

    @staticmethod
    def time_to_mysql(t):
        """ Convert time struct to MySQL format. """
        if type(t) == float or type(t) == int:
            t = time.localtime(t)
        return time.strftime('%Y-%m-%d %H:%M:%S', t)

    def execute_fetchall_commit(self, query, params=None):
        self.cursor.execute(query, params)
        rows = self.cursor.fetchall()
        self.connection.commit()
        return rows

    def get_src_dst_pairs(self):
        query = "SELECT id,INET_NTOA(src) AS src,INET_NTOA(dst) AS dst FROM src_dst"
        self.cursor.execute(query)
        rows = self.cursor.fetchall()
        return rows

    def src_dst_id(self, src, dst):
        """ Gets the ID of the src-dst pair from the DB, maybe creating the entry.

        Create a new src-dst pair in the DB if it does not already exist.
        Maintains a cache of src-dst pairs in memory.

        Returns the ID of src-dst pair. """
        params = (src, dst)
        if params in self.src_dst_pairs:
            return self.src_dst_pairs[params]
        query = "SELECT id FROM src_dst WHERE src=INET_ATON(%s) \
                 AND dst=INET_ATON(%s)"
        self.cursor.execute(query, params)
        result = self.cursor.fetchone()
        if not result:
            # we need to create the src-dst pair
            query = "INSERT INTO src_dst (src,dst) VALUES \
                     (INET_ATON(%s),INET_ATON(%s))"
            self.cursor.execute(query, params)
            self.connection.commit()
            pair_id = self.cursor.lastrowid
        else:
            pair_id = result['id']
        self.src_dst_pairs[params] = pair_id
        return pair_id

    def get_poll_counts_by_pair(self):
        query = "SELECT src_dst,count(*) AS count FROM output GROUP BY src_dst"
        self.cursor.execute(query)
        rows = self.cursor.fetchall()
        self.connection.commit()
        return rows

    def get_poll_data_by_pair(self, pair_id, start=None, stop=None):
        """ Get poll data from DB for specific src_dst pair.

            Optionally specify the time window with epoch numbers
            or time structs.

            Returns a list of rows from the database.
            Each row is a mapping with keys 'time' and 'latency'.
        """
        if stop is None:
            stop = time.time()
        if start is None:
            start = stop - 3601
        query = "SELECT time,latency FROM output WHERE src_dst=%s AND time > %s AND time < %s"
        if not type(pair_id) is int:
            raise TypeError("pair_id must be an integer.")
        params = (pair_id,
                  DatabaseMysql.time_to_mysql(start),
                  DatabaseMysql.time_to_mysql(stop))
        rows = self.execute_fetchall_commit(query, params)
        return rows

    def record_poll_data(self, src_ip, dst_ip, send_time, receive_time):
        """ Record results of a single poll in the database. """
        latency = Database.time_diff_to_short_latency(send_time, receive_time)
        pair_id = self.src_dst_id(src_ip, dst_ip)
        send_datetime = datetime.datetime.fromtimestamp(send_time)
        query = "INSERT INTO output (time, src_dst, latency) \
                             VALUES (%s, %s, %s)"
        params = (send_datetime, pair_id, latency)
        self.cursor.execute(query, params)
        self.connection.commit()

