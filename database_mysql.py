#!/usr/bin/python3
"""
Database abstraction layer
"""

import mysql.connector
import time

from database import Database


class DatabaseMysql(Database):
    def __init__(self, db_params):
        self.connection = None
        self.cursor = None
        super().__init__()
        self.db_params = db_params
        self._connect_db()

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

    def get_poll_counts_by_pair(self):
        query = "SELECT src_dst,count(*) AS count FROM output GROUP BY src_dst"
        self.cursor.execute(query)
        rows = self.cursor.fetchall()
        self.connection.commit()
        return rows

    def get_poll_data_by_pair(self, pair_id,
                              start=time.time() - 3601,
                              stop=time.time()):
        query = "SELECT time,latency FROM output WHERE src_dst=%s AND time > %s AND time < %s"
        if not type(pair_id) is int:
            raise TypeError("pair_id must be an integer.")
        params = (pair_id,
                  DatabaseMysql.time_to_mysql(start),
                  DatabaseMysql.time_to_mysql(stop))
        rows = self.execute_fetchall_commit(query, params)
        return rows
