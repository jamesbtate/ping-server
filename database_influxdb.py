#!/usr/bin/env python3
"""
Database abstraction layer
"""

from influxdb import InfluxDBClient
import operator
import datetime
import logging
import time
import sys
import os

# from functools import lru_cache
# from cachetools import LRUCache, cachedmethod

from database import Database
from database_mysql import DatabaseMysql
from datafile import Datafile


class DatabaseBinary(Database):
    DEFAULT_MAX_RECORDS = 604800
    
    def __init__(self, db_params):
        self.db_params = db_params
        self.client = None
        super().__init__()
        self.databaseMysql = DatabaseMysql(db_params)
        client = InfluxDBClient(db_params['influxdb_host'], db_params['influxdb_port'], db_params['influxdb_user'],
                                db_params['influxdb_pass'], db_params['influxdb_db'])
        client.create_database('ping')  # this does nothing if the DB already exists. I think.
        # self.cache = LRUCache(maxsize=1048576, getsizeof=len)

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

    def get_poll_counts_by_pair(self):
        pass

    # @cachedmethod(operator.attrgetter('cache'))
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

    def record_poll_data(self, src_ip, dst_ip, send_time, receive_time):
        """ Record results of a single poll in the database. """
        point = {
            "measurement": "icmp-echo",
            "tags": {
                "probe": "[unimplemented]",
                "src_ip": src_ip,
                "dst_ip": dst_ip
            },
            "time": send_time,
            "fields": {
                "latency": receive_time - send_time
            }
        }
        self.client.write_points([point])

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

    def read_record(self):
        """ Read a data record at the current position in the file.

            Decodes the stored data.
        """
        record_bytes = self.file.read(self.record_length)
        record = self.record_struct.unpack(record_bytes)
        latency = Database.short_latency_to_seconds(record[1])
        return [record[0], latency]

    def read_n_records(self, n):
        """ Read multiple records at the current position in the file.

            Returns a list of lists: one sublist for each decoded record
        """
        records = []
        data = self.file.read(self.record_length * n)
        if not data:
            return records
        records_read = len(data) // self.record_length
        if len(data) % self.record_length != 0:
            logging.warning("Read %i bytes not divisible by record length: %i",
                            len(data), self.record_length)
        if records_read != n:
            logging.warning("Read fewer bytes than expected: %i/%i",
                            len(data), n * self.record_length)
        read_struct = self.get_multiple_record_struct(len(data) //
                                                      self.record_length)
        all_values = read_struct.unpack(data)
        for i in range(records_read):
            epoch = all_values[i * 2]
            latency = Database.short_latency_to_seconds(all_values[i * 2 + 1])
            records.append([epoch, latency])
        return records

    def read_all_records(self):
        """ Read all records from a file in order.

            Returns: a list of records, each represented as a list of epoch
            timestamp and decoded latency.
            Example: [[timestamp, decoded latency],...]
        """
        all_records = []
        self.file.seek(self.offset)
        remaining_records = self.number_of_records
        while True:
            pos = self.file.tell()
            current_file_length = self.number_of_records * self.record_length \
                                  + self.header_length
            if pos >= current_file_length:
                self.file.seek(self.header_length)
                pos = self.header_length
            bytes_left_to_eof = current_file_length - pos
            records_left_to_eof = bytes_left_to_eof // self.record_length
            read = min(1000, records_left_to_eof, remaining_records)
            records = self.read_n_records(read)
            all_records += records
            remaining_records -= len(records)
            if remaining_records <= 0:
                break
        logging.debug("Read %i records from %s", len(records), self.file.name)
        return all_records

    def read_all_values(self):
        """ Read all values from a file in order.

            Returns: a list of timestamps interleaved with the encoded latency
            values.
        """
        all_values = []
        self.file.seek(self.offset)
        remaining_records = self.number_of_records
        while True:
            pos = self.file.tell()
            current_file_length = self.number_of_records * self.record_length \
                                  + self.header_length
            if pos >= current_file_length:
                self.file.seek(self.header_length)
                pos = self.header_length
            bytes_left_to_eof = current_file_length - pos
            records_left_to_eof = bytes_left_to_eof // self.record_length
            read = min(1000, records_left_to_eof, remaining_records)
            values = self.read_n_value_pairs(read)
            all_values += values
            remaining_records -= int(len(values) / 2)
            if remaining_records <= 0:
                break
        logging.debug("Read %i value-pairs from %s", len(all_values),
                      self.file.name)
        return all_values

    def read_records(self, start_time, end_time):
        """ Return the list of records from start to end times, inclusive.

            start_time and end_time are UNIX epoch seconds.
            If there are no records within the time range, [] is returned.

            Sample return:
                [(epoch-integer, 123), (epoch-integer+1, 65534), ...]
        """
        values_list = self.read_all_values()
        if values_list[0] > end_time:
            logging.debug("First record (%i) was after end_time: %i",
                          values_list[0], end_time)
            return []
        if values_list[-2] < start_time:
            logging.debug("Last record (%i) was before start_time: %i",
            values_list[-2], start_time)
            return []
        # if we get to this point, we will always return at least one record.
        # don't bother with binary search for now
        first = 0
        for i in range(0, len(values_list), 2):
            if values_list[i] >= start_time:
                first = i
                break
        last = len(values_list) - 1
        for i in range(first + 2, len(values_list), 2):
            if values_list[i] > end_time:
                last = i
                break
        specific_records = []
        for i in range(first, last, 2):
            latency = Database.short_latency_to_seconds(values_list[i+1])
            specific_records.append([values_list[i], latency])
        logging.debug("Got %i specific records from %i to %i",
                      len(specific_records), start_time, end_time)
        return specific_records
