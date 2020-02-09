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


TIMEOUT_VALUE = 127.0  # magic value indicating probe timed out
LATENCY_PRECISION = 4  # number of decimals on the latency value (seconds)
                       #  4 means #.#### seconds is the latency precision
                       #  which is precise to 100us (0.1ms)


class DatabaseInfluxDB(Database):
    def __init__(self, db_params):
        self.db_params = db_params
        self.client = None
        super().__init__()
        self.databaseMysql = DatabaseMysql(db_params)
        self.client = InfluxDBClient(db_params['influxdb_host'],
                                     db_params['influxdb_port'],
                                     db_params['influxdb_user'],
                                     db_params['influxdb_pass'],
                                     db_params['influxdb_db'])
        logging.info("Connected to InfluxDB @ %s", db_params['influxdb_host'])
        # this does nothing if the DB already exists. I think.
        self.client.create_database('ping')
        self.client.alter_retention_policy('autogen', duration='4w', shard_duration='1d')
        # self.cache = LRUCache(maxsize=1048576, getsizeof=len)

    def get_src_dst_pairs(self):
        return self.databaseMysql.get_src_dst_pairs()

    def get_src_dst_by_id(self, pair_id):
        """ Gets a source-destination pair from the database by ID number. """
        return self.databaseMysql.get_src_dst_by_id(pair_id)

    def src_dst_id(self, src, dst):
        """ Gets the ID of the src-dst pair from the DB, maybe creating the entry.

        Create a new src-dst pair in the DB if it does not already exist.
        Maintains a cache of src-dst pairs in memory.

        Returns the ID of src-dst pair. """
        return self.databaseMysql.src_dst_id(src, dst)

    def get_poll_counts_by_pair(self, src_ip, dst_ip) -> int:
        """ Return the number of polls for a specific pair. """
        query = 'SELECT COUNT(latency) FROM "icmp-echo" WHERE ' + \
                'src_ip=$src_ip AND dst_ip=$dst_ip'
        params = {
            'src_ip': src_ip,
            'dst_ip': dst_ip,
        }
        logging.debug("Querying: %s | %s", query, params)
        result_set = self.client.query(query, bind_params=params, epoch='s')
        points = list(result_set.get_points())
        return points[0]['count']

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
            end = int(time.time())
        if start is None:
            start = end - 3601
        src_dst = self.get_src_dst_by_id(pair_id)
        src_ip = src_dst['src']
        dst_ip = src_dst['dst']
        records = self.read_records(src_ip, dst_ip, start, end)
        if convert_to_datetime:
            for record in records:
                # record['time'] = datetime.datetime.strptime(record['time'], "%Y-%m-%dT%H:%M:%SZ")
                record['time'] = datetime.datetime.fromtimestamp(record['time'])
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
            latency = record['latency']
            if latency is None or latency == TIMEOUT_VALUE:
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
        # do this to make sure there is a record created in the MySQL DB for this pair.
        pair_id = self.src_dst_id(src_ip, dst_ip)
        if receive_time is None:
            latency = TIMEOUT_VALUE
        else:
            latency = round(receive_time - send_time, LATENCY_PRECISION)
        point = {
            "measurement": "icmp-echo",
            "tags": {
                "probe": "[unimplemented]",
                "src_ip": src_ip,
                "dst_ip": dst_ip
            },
            "time": int(send_time),
            "fields": {
                "latency": latency
            }
        }
        self.client.write_points([point], time_precision='s')

    def last_poll_time_by_pair(self, src_ip, dst_ip) -> datetime.datetime:
        """ Get the last time a particular pair ID was polled.

        Returns a datetime.datetime object.
        """
        query = 'SELECT LAST(*) FROM "icmp-echo" WHERE ' + \
                'src_ip=$src_ip AND dst_ip=$dst_ip'
        params = {
            'src_ip': src_ip,
            'dst_ip': dst_ip,
        }
        logging.debug("Querying: %s | %s", query, params)
        result_set = self.client.query(query, bind_params=params, epoch='s')
        points = list(result_set.get_points())
        dt = datetime.datetime.fromtimestamp(points[0]['time'])
        return dt

    def read_records(self, src_ip, dst_ip, start_time, end_time):
        """ Return the list of records from start to end times, inclusive.

            start_time and end_time are UNIX epoch seconds.
            If there are no records within the time range, [] is returned.

            Sample return:
                [{'1970-01-01T12:34:56}, 0.0123}, {...}, ...]
        """
        start_time = str(int(start_time))
        end_time = str(int(end_time))
        query = 'SELECT "latency" FROM "icmp-echo" WHERE src_ip=$src_ip AND ' + \
                'dst_ip=$dst_ip AND time>=' + start_time + 's AND time<=' + end_time + 's'
        params = {
            'src_ip': src_ip,
            'dst_ip': dst_ip,
        }
        logging.debug("Querying: %s | %s", query, params)
        result_set = self.client.query(query, bind_params=params, epoch='s')
        points = list(result_set.get_points())
        logging.debug("Got %i records from %i to %i", len(points), start_time, end_time)
        return points
