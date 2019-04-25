#!/usr/bin/python3
"""
Database abstraction layer
"""

from abc import ABC, abstractmethod
import mysql.connector
from database import Database
from server import read_config


class DatabaseMysql(Database):
    def __init__(self):
        self.connection = None
        self.cursor = None
        super().__init__()
        parser = read_config()
        self.db_params = parser['server']
        self._connect_db()

    def _connect_db(self):
        c = mysql.connector.connect(user=self.db_params['db_user'],
                                    password=self.db_params['db_pass'],
                                    host=self.db_params['db_host'],
                                    database=self.db_params['db_db'])
        self.connection = c
        self.cursor = self.connection.cursor(dictionary=True)

    def get_src_dst_pairs(self):
        query = "SELECT id,INET_NTOA(src) AS src,INET_NTOA(dst) AS dst FROM src_dst"
        self.cursor.execute(query)
        rows = self.cursor.fetchall()
        return rows
