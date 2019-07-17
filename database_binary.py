#!/usr/bin/env python3
"""
Database abstraction layer
"""

import time
import os

from database import Database
from database_mysql import DatabaseMysql
from datafile import Datafile


class DatabaseBinary(Database):
    def __init__(self, db_params):
        self.db_params = db_params
        self.connection = None
        self.cursor = None
        super().__init__()
        self.datafiles = {}  # mapping of src-dst IP tuples to Datafiles
        self.databaseMysql = DatabaseMysql(db_params)

    def get_src_dst_pairs(self):
        return self.databaseMysql.get_binary_src_dst_pairs()

    def get_src_dst_by_id(self, id):
        """ Gets a source-destination pair from the database by ID number. """
        pass

    def src_dst_id(self, src, dst):
        """ Gets the ID of the src-dst pair from the DB, maybe creating the entry.

        Create a new src-dst pair in the DB if it does not already exist.
        Maintains a cache of src-dst pairs in memory.

        Returns the ID of src-dst pair. """
        pass

    def get_data_file_handle(self, src, dst):
        """ Get a handle to the data file, opened for binary writing.

            Uses the cache of handles in self.src_dst_handles. If the file
            is not already open, open it.
        """

    def get_poll_counts_by_pair(self):
        pass

    def get_poll_data_by_pair(self, pair_id, start=None, stop=None):
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
        """
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
        """

    def get_or_make_datafile(self, src_ip, dst_ip):
        if (src_ip, dst_ip) in self.datafiles:
            return self.datafiles[(src_ip, dst_ip)]
        # check if pair is in DB already and return it
        binary_pair = self.databaseMysql.get_binary_src_dst_by_pair(src_ip,
                                                                    dst_ip)
        if binary_pair:
            datafile = Datafile.open_datafile(binary_pair['id'],
                                              binary_pair['binary_file'])
        # otherwise, make a new pair in the DB
        else:
            directory = self.db_params['binary_data_directory']
            filename = src_ip + '_' + dst_ip + '_' + str(int(time.time())) \
                + '.ping'
            binary_file = os.path.join(directory, filename)
            pair_id = self.databaseMysql.make_binary_src_dst_pair(src_ip,
                                                                  dst_ip,
                                                                  binary_file)
            datafile = Datafile.create_new_datafile(pair_id, binary_file)
        self.datafiles[(src_ip, dst_ip)] = datafile
        return datafile

    def record_poll_data(self, src_ip, dst_ip, send_time, receive_time):
        """ Record results of a single poll in the database. """
        latency = Database.time_diff_to_short_latency(send_time, receive_time)
        datafile = self.get_or_make_datafile(src_ip, dst_ip)
        datafile.record_datum(int(send_time), latency)
