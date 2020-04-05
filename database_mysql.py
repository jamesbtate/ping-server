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


class DatabaseMysql(object):
    def __init__(self, db_params):
        self.connection: MySQLConnection = None
        self.cursor: MySQLCursor = None
        super().__init__()
        self.db_params = db_params
        self.user = self.db_params['db_user']
        self.password = self.db_params['db_pass']
        self.host = self.db_params['db_host']
        self.port = self.db_params['db_port']
        self.database = self.db_params['db_db']
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
            logging.debug("Connected to database %s:%s:%s", self.host, self.port, self.database)
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
                raise e from None
            self._connect_db()
            self.execute(query, params)

    def commit(self):
        """ Calls commit() on the underlying MySQL connection. """
        self.connection.commit()

    def execute_commit(self, query: str, params: Iterable = None) -> None:
        """ Wrapper for execute + commit. """
        self.execute(query, params)
        self.connection.commit()

    def execute_fetchall_commit(self, query: str, params: Iterable = None) -> list:
        """ Wrapper for execute, fetchall and commit.

            Sometimes database returns cached result if you don't commit.
        """
        self.execute(query, params)
        rows = self.cursor.fetchall()
        self.connection.commit()
        return rows

    def get_tables(self):
        """ Return a list of the names of the tables in the database """
        rows = self.execute_fetchall_commit("SHOW TABLES")
        table_names = [tuple(_.values())[0] for _ in rows]
        logging.debug("Tables: %s", table_names)
        return table_names

    def get_db_version(self) -> int:
        """ Get the version integer of the schema in the database

        If the version table is not defined, version 0 is assumed.
        If the version table and the src_dst table is not defined, version -1 is assumed.

        """
        table_names = self.get_tables()
        if 'src_dst' not in table_names:
            return -1
        elif 'version' not in table_names:
            return 0
        version = self.execute_fetchall_commit("SELECT * FROM version")[0]['ping_schema']
        return version

    def get_prober_id_by_name(self, name: str) -> int:
        """ Gets a prober ID from the database by name string. """
        query = "SELECT id FROM prober WHERE name=%s"
        rows = self.execute_fetchall_commit(query, (name,))
        if not rows:
            raise ValueError("No prober with name: " + str(name))
        return rows[0]['id']

    def get_src_dst_pairs(self):
        query = "SELECT src_dst.id,prober.name as prober_name,INET_NTOA(dst) AS dst " + \
                "FROM src_dst JOIN prober on src_dst.prober_id=prober.id"
        rows = self.execute_fetchall_commit(query)
        return rows

    def get_src_dst_by_id(self, id):
        """ Gets a source-destination pair from the database by ID number. """
        query = "SELECT src_dst.id,prober.name as prober_name,prober_id,INET_NTOA(dst) AS dst \
                 FROM src_dst JOIN prober ON src_dst.prober_id=prober.id WHERE src_dst.id=%s"
        rows = self.execute_fetchall_commit(query, (id,))
        if not rows:
            raise ValueError("No source-destination pair with ID# " + str(id))
        return rows[0]

    def src_dst_id(self, prober_name, dst):
        """ Gets the ID of the src-dst pair from the DB, maybe creating the entry.

        Create a new src-dst pair in the DB if it does not already exist.
        Maintains a cache of src-dst pairs in memory.

        Returns the ID of src-dst pair. """
        select_params = (dst, prober_name)
        if select_params in self.src_dst_pairs:
            return self.src_dst_pairs[select_params]
        query = "SELECT src_dst.id AS id FROM src_dst JOIN prober ON src_dst.prober_id=prober.id \
                WHERE dst=INET_ATON(%s) AND prober.name=%s"
        rows = self.execute_fetchall_commit(query, select_params)
        if not rows:
            # we need to create the src-dst pair
            prober_id = self.get_prober_id_by_name(prober_name)
            insert_params = (prober_id, dst)
            query = "INSERT INTO src_dst (prober_id,dst) VALUES (%s, INET_ATON(%s));"
            self.execute_commit(query, insert_params)
            pair_id = self.cursor.lastrowid
            logging.debug("Added pair ID %i to src_dst table", pair_id)
        else:
            result = rows[0]
            pair_id = result['id']
        self.src_dst_pairs[select_params] = pair_id
        return pair_id
