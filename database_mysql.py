#!/usr/bin/env python3
"""
Database abstraction layer
"""

import mysql.connector
from mysql.connector import MySQLConnection
from mysql.connector.errors import DatabaseError, OperationalError
from mysql.connector.cursor import MySQLCursor
from typing import Iterable
import datetime
import logging
import time

from database import Database


class DatabaseMysql(Database):
    def __init__(self, db_params):
        self.connection: MySQLConnection = None
        self.cursor: MySQLCursor = None
        super().__init__()
        self.db_params = db_params
        self.src_dst_pairs = {}
        self._connect_db()

    def _connect_db(self):
        try:
            c = mysql.connector.connect(user=self.db_params['db_user'],
                                        password=self.db_params['db_pass'],
                                        host=self.db_params['db_host'],
                                        port=self.db_params['db_port'],
                                        database=self.db_params['db_db'],
                                        charset='utf8'
                                        )
            self.connection = c
            self.cursor = self.connection.cursor(dictionary=True)
        except DatabaseError as e:
            logging.error(str(e))

    @staticmethod
    def time_to_mysql(t):
        """ Convert time struct to MySQL format. """
        if type(t) == float or type(t) == int:
            t = time.localtime(t)
        return time.strftime('%Y-%m-%d %H:%M:%S', t)

    def execute(self, query: str, params: Iterable = None) -> None:
        """ Wrapper for executing queries that recovers from some connection errors. """
        if self.cursor is None:
            try:
                self._connect_db()
            except DatabaseError as e:
                logging.error(str(e))
                raise
        try:
            self.cursor.execute(query, params)
        except DatabaseError or OperationalError as e:
            if e.errno == 2006:
                logging.info("MySQL server went away. Reconnecting...")
            elif e.errno == 2013:
                logging.info("Lost connection to MySQL server. Reconnecting...")
            elif e.errno == 2055:
                logging.info("Lost connection to MySQL server. Broken Pipe. Reconnecting...")
            else:
                raise
            self._connect_db()
            self.execute(query, params)

    def execute_commit(self, query: str, params: Iterable = None) -> None:
        """ Wrapper for execute + commit. """
        self.execute(query, params)
        self.connection.commit()

    def execute_fetchall_commit(self, query: str, params: Iterable = None) -> Iterable:
        """ Wrapper for execute, fetchall and commit.

            Sometimes database returns cached result if you don't commit.
        """
        self.execute(query, params)
        rows = self.cursor.fetchall()
        self.connection.commit()
        return rows

    def get_src_dst_pairs(self):
        query = "SELECT id,INET_NTOA(src) AS src,INET_NTOA(dst) AS dst " + \
                "FROM src_dst"
        rows = self.execute_fetchall_commit(query)
        return rows

    def get_src_dst_by_id(self, id):
        """ Gets a source-destination pair from the database by ID number. """
        query = "SELECT id,INET_NTOA(src) AS src,INET_NTOA(dst) AS dst " + \
                "FROM src_dst WHERE id=%s"
        rows = self.execute_fetchall_commit(query, (id,))
        if not rows:
            raise ValueError("No source-destination pair with ID# " + str(id))
        return rows[0]

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
        rows = self.execute_fetchall_commit(query, params)
        if not rows:
            # we need to create the src-dst pair
            query = "INSERT INTO src_dst (src,dst) VALUES \
                     (INET_ATON(%s),INET_ATON(%s))"
            self.execute_commit(query, params)
            pair_id = self.cursor.lastrowid
            logging.debug("Added pair ID %i to src_dst table", pair_id)
        else:
            result = rows[0]
            pair_id = result['id']
        self.src_dst_pairs[params] = pair_id
        return pair_id

    def get_poll_counts_by_pair(self):
        query = "SELECT src_dst,count(*) AS count FROM output GROUP BY src_dst"
        rows = self.execute_fetchall_commit(query)
        return rows

    def get_poll_data_by_id(self, pair_id, start=None, stop=None):
        """ Get poll data from DB for specific src_dst pair.

            Optionally specify the time window with epoch numbers
            or time structs.

            Returns a list of rows from the database.
            Each row is a mapping with keys 'time' and 'latency'.
            The time is Python time object.
            The latency is the number of seconds latency (float).
            A latency value of None indicates a timeout.
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
        for row in rows:
            row['latency'] = Database.short_latency_to_seconds(row['latency'])
        return rows

    def record_poll_data(self, src_ip, dst_ip, send_time, receive_time):
        """ Record results of a single poll in the database. """
        latency = Database.time_diff_to_short_latency(send_time, receive_time)
        pair_id = self.src_dst_id(src_ip, dst_ip)
        send_datetime = datetime.datetime.fromtimestamp(send_time)
        query = "INSERT INTO output (time, src_dst, latency) \
                             VALUES (%s, %s, %s)"
        params = (send_datetime, pair_id, latency)
        self.execute_commit(query, params)

    def get_binary_src_dst_pairs(self):
        query = "SELECT id, INET_NTOA(src) AS src, INET_NTOA(dst) AS dst, " + \
                "binary_file, max_records FROM binary_src_dst"
        rows = self.execute_fetchall_commit(query)
        return rows

    def get_binary_src_dst_by_id(self, id):
        """ Gets a binary src-dst pair from the database by ID number. """
        query = "SELECT id, INET_NTOA(src) AS src, INET_NTOA(dst) AS dst, " + \
                "binary_file, max_records FROM binary_src_dst WHERE id=%s"
        rows = self.execute_fetchall_commit(query, (id,))
        if not rows:
            raise ValueError("No binary src-dst pair with ID# " + str(id))
        return rows[0]

    def get_binary_src_dst_by_pair(self, src_ip, dst_ip):
        params = (src_ip, dst_ip)
        query = "SELECT * FROM binary_src_dst WHERE src=INET_ATON(%s) \
                 AND dst=INET_ATON(%s)"
        rows = self.execute_fetchall_commit(query, params)
        if not rows:
            return rows
        return rows[0]

    def make_binary_src_dst_pair(self, src, dst, binary_file, max_records):
        """ Make an entry in the database for a src-dst pair with data file.

        Args:
        binary_file: path to data file
        """
        query = "INSERT INTO binary_src_dst (src,dst,binary_file,max_records) \
                 VALUES (INET_ATON(%s), INET_ATON(%s), %s, %s)"
        params = (src, dst, binary_file, max_records)
        self.execute_commit(query, params)
        pair_id = self.cursor.lastrowid
        logging.info("Created new binary pair: %i %s to %s", pair_id, src, dst)
        return pair_id
