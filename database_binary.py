#!/usr/bin/env python3
"""
Database abstraction layer
"""

import operator
import datetime
import time
import sys
import os

from functools import lru_cache
from cachetools import LRUCache, cachedmethod

from database import Database
from database_mysql import DatabaseMysql
from datafile import Datafile


class DatabaseBinary(Database):
    DEFAULT_MAX_RECORDS = 604800
    
    def __init__(self, db_params):
        self.db_params = db_params
        self.connection = None
        self.cursor = None
        super().__init__()
        self.datafiles = {}  # mapping of src-dst IP tuples to Datafiles
        self.databaseMysql = DatabaseMysql(db_params)
        self.cache = LRUCache(maxsize=1048576, getsizeof=len)

    def get_src_dst_pairs(self):
        return self.databaseMysql.get_binary_src_dst_pairs()

    def get_src_dst_by_id(self, pair_id):
        """ Gets a source-destination pair from the database by ID number. """
        return self.databaseMysql.get_binary_src_dst_by_id(pair_id)

    def src_dst_id(self, src, dst):
        """ Gets the ID of the src-dst pair from the DB, maybe creating the entry.

        Create a new src-dst pair in the DB if it does not already exist.
        Maintains a cache of src-dst pairs in memory.

        Returns the ID of src-dst pair. """
        pass

    def get_datafile_handle(self, pair_id):
        """ Get a handle to the data file, opened for binary writing. """
        src_dst = self.get_src_dst_by_id(pair_id)
        datafile = Datafile.open_datafile(src_dst['id'],
                                          src_dst['binary_file'],
                                          max_records=src_dst['max_records'])
        return datafile

    def get_poll_counts_by_pair(self):
        pass

    @cachedmethod(operator.attrgetter('cache'))
    def get_poll_data_by_id(self, pair_id, start=None, end=None,
                            convert_to_datetime=False):
        """ Get poll data from DB for specific src_dst pair.

            Optionally specify the time window with epoch numbers
            or time structs.

            Returns a list of rows from the database.
            Each row is a list with two items: time and latency.
            The time is integer UNIX time, unless convert_to_datetime is True.
            The latency is the number of seconds latency (float).
            A latency value of None indicates a timeout.
        """
        if end is None:
            end = time.time()
        if start is None:
            start = end - 3601
        datafile = self.get_datafile_handle(pair_id)
        records = datafile.read_records(start, end)
        if convert_to_datetime:
            for record in records:
                record[0] = datetime.datetime.fromtimestamp(record[0])
        return records

    @staticmethod
    def calculate_statistics(records):
        """ Calculate some statistics for a list of records.

            Returns a dictionary of statistical values for the list of records.
            Statistics := {
                'echos': 1801  # number of echo requests
                'successes': 1234  # count of successful responses
                'timeouts': 567  # count of "no response receive"
                'success_rate': 0.712  # fraction of requests that succeeded
                'mean': 0.123  # average latency, not considering timeouts
                'minimum': 0.001
                'maximum': 0.876  # does not account for infinite timeout
            }
        """
        minimum = sys.float_info.max
        maximum = sys.float_info.min
        total = 0.0
        successes = 0
        timeouts = 0
        mean = 0.0
        success_rate = 0.0
        for record in records:
            latency = record[1]
            if latency is None:
                timeouts += 1
                continue
            successes += 1
            total += latency
            if latency < minimum:
                minimum = latency
            if latency > maximum:
                maximum = latency
        if records:
            mean = total / successes
            success_rate = successes / len(records)
        statistics = {
            'echos': len(records),
            'successes': successes,
            'timeouts': timeouts,
            'success_rate': success_rate,
            'mean': mean,
            'minimum': minimum,
            'maximum': maximum
        }
        return statistics

    def get_or_make_datafile(self, src_ip, dst_ip):
        if (src_ip, dst_ip) in self.datafiles:
            return self.datafiles[(src_ip, dst_ip)]
        # check if pair is in DB already and return it
        binary_pair = self.databaseMysql.get_binary_src_dst_by_pair(src_ip,
                                                                    dst_ip)
        if binary_pair:
            datafile = self.get_datafile_handle(binary_pair['id'])
        # otherwise, make a new pair in the DB
        else:
            directory = self.db_params['binary_data_directory']
            filename = src_ip + '_' + dst_ip + '_' + str(int(time.time())) \
                + '.ping'
            binary_file = os.path.join(directory, filename)
            pair_id = self.databaseMysql.make_binary_src_dst_pair(src_ip,
                                                                  dst_ip,
                                                                  binary_file,
                                                                  DatabaseBinary.DEFAULT_MAX_RECORDS)
            datafile = Datafile.create_new_datafile(pair_id, binary_file,
                                                    max_records=DatabaseBinary.DEFAULT_MAX_RECORDS)
        self.datafiles[(src_ip, dst_ip)] = datafile
        return datafile

    def record_poll_data(self, src_ip, dst_ip, send_time, receive_time):
        """ Record results of a single poll in the database. """
        datafile = self.get_or_make_datafile(src_ip, dst_ip)
        datafile.record_datum(int(send_time), send_time, receive_time)

    def get_file_modification_time(self, path, iso8601=False):
        """ Returns the UNIX time of when a file was last modified.

            Arguments:
                path: path to the file on the filesystem

            Returns a float for the UNIX/epoch time of file modification.
            If iso8601 is True, return a formatted string instead.
            May raise an error if the file cannot be stat-ed.
        """
        mtime = os.stat(path).st_mtime
        if iso8601:
            dt = datetime.datetime.fromtimestamp(mtime)
            date_string = dt.isoformat()
            return date_string
        else:
            return mtime
