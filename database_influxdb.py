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

from cachetools import TTLCache, cachedmethod, cached
from typing import List, Iterable

from database import Database
from pingweb.models import SrcDst, Prober
import env


TIMEOUT_VALUE = 127.0  # magic value indicating probe timed out
LATENCY_PRECISION = 4  # number of decimals on the latency value (seconds)
                       #  4 means #.#### seconds is the latency precision
                       #  which is precise to 100us (0.1ms)

src_dst_pairs = {}  # a dumb infinite cache of SrcDst pair IDs
class_cache = TTLCache(maxsize=8192, ttl=60)


class DatabaseInfluxDB(Database):
    def __init__(self, db_params=None):
        self.db_params = db_params
        self.client = None
        super().__init__()
        self.cache = TTLCache(maxsize=1048576, ttl=60, getsizeof=len)

    def _connect(self):
        """ Connect to the InfluxDB server. Load params if not specified. """
        if not self.db_params:
            self.db_params = env.get_influxdb_params()
        self.client = InfluxDBClient(self.db_params['INFLUXDB_HOST'],
                                     self.db_params['INFLUXDB_PORT'],
                                     self.db_params['INFLUXDB_USER'],
                                     self.db_params['INFLUXDB_PASS'],
                                     self.db_params['INFLUXDB_DB'])
        logging.info("Connected to InfluxDB @ %s", self.db_params['INFLUXDB_HOST'])
        # this does nothing if the DB already exists. I think.
        self.client.create_database('ping')
        self.client.alter_retention_policy('autogen', duration='4w', shard_duration='1d')

    @staticmethod
    def get_prober_id_by_name(prober_name: str) -> int:
        """ Returns the ID of the prober with the given name. """
        return Prober.objects.get(name=prober_name).id

    @staticmethod
    def get_src_dst_pairs() -> Iterable[SrcDst]:
        return SrcDst.objects.all()

    @staticmethod
    def get_src_dst_by_id(pair_id) -> SrcDst:
        """ Gets a source-destination pair from the database by ID number. """
        return SrcDst.objects.get(id=pair_id)

    @staticmethod
    @cached(class_cache)
    def src_dst_id(prober_name, dst) -> int:
        """ Gets the ID of the src-dst pair from the DB, maybe creating the entry.

        Create a new src-dst pair in the DB if it does not already exist.

        Returns the ID of src-dst pair.
        """
        objects = SrcDst.objects.filter(prober__name=prober_name, dst=dst)
        if not objects:
            # we need to create the src-dst pair
            prober_id = DatabaseInfluxDB.get_prober_id_by_name(prober_name)
            src_dst = SrcDst()
            src_dst.prober_id = prober_id
            src_dst.dst = dst
            src_dst.save()
            pair_id = src_dst.id
            logging.debug("Added SrcDst ID %i to database", pair_id)
        else:
            result = objects[0]
            pair_id = result.id
        return pair_id

    def get_poll_counts_by_pair(self, prober_name, dst_ip) -> int:
        """ Return the number of polls for a specific pair. """
        if not self.client:
            self._connect()
        query = 'SELECT COUNT(latency) FROM "icmp-echo" WHERE ' + \
                'prober_name=$prober_name AND dst_ip=$dst_ip'
        params = {
            'prober_name': prober_name,
            'dst_ip': dst_ip,
        }
        logging.debug("Querying: %s | %s", query, params)
        result_set = self.client.query(query, bind_params=params, epoch='s')
        points = list(result_set.get_points())
        if not points:
            return 0
        return points[0]['count']

    @cachedmethod(operator.attrgetter('cache'))
    def get_poll_data_by_id(self, pair_id, start=None, end=None,
                            convert_to_datetime=False):
        """ Get poll data from DB for specific src_dst pair.

            Optionally specify the time window with datetime.datetime objects.

            Returns a list of rows from the database.
            Each row is a list with two items: time and latency.
            The time is integer UNIX time, unless convert_to_datetime is True.
            The latency is the number of seconds latency (float).
            A latency value of None indicates a timeout.
        """
        if end is None:
            end = datetime.datetime.now()
        if start is None:
            start = end - datetime.timedelta(seconds=3601)
        src_dst = self.get_src_dst_by_id(pair_id)
        prober_name = src_dst.prober.name
        dst_ip = src_dst.dst
        records = self.read_records(prober_name, dst_ip, start, end)
        if convert_to_datetime:
            for record in records:
                # record['time'] = datetime.datetime.strptime(record['time'], "%Y-%m-%dT%H:%M:%SZ")
                record['time'] = datetime.datetime.fromtimestamp(record['time'])
        return records

    @staticmethod
    def calculate_statistics(records) -> dict:
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
        if successes:
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

    def record_poll_data(self, prober_name, dst_ip, send_time, receive_time) -> None:
        """ Record results of a single poll in the database. """
        if not self.client:
            self._connect()
        # do this to make sure there is a record created in the MySQL DB for this pair.
        pair_id = self.src_dst_id(prober_name, dst_ip)
        if receive_time is None:
            latency = TIMEOUT_VALUE
        else:
            latency = round(receive_time - send_time, LATENCY_PRECISION)
        point = {
            "measurement": "icmp-echo",
            "tags": {
                "probe": "[unimplemented]",
                "prober_name": prober_name,
                "dst_ip": dst_ip
            },
            "time": int(send_time),
            "fields": {
                "latency": latency
            }
        }
        self.client.write_points([point], time_precision='s')

    def last_poll_time_by_pair(self, prober_name, dst_ip) -> datetime.datetime:
        """ Get the last time a particular pair ID was polled.

        Returns a datetime.datetime object.
        """
        if not self.client:
            self._connect()
        query = 'SELECT LAST(*) FROM "icmp-echo" WHERE ' + \
                'prober_name=$prober_name AND dst_ip=$dst_ip'
        params = {
            'prober_name': prober_name,
            'dst_ip': dst_ip,
        }
        logging.debug("Querying: %s | %s", query, params)
        result_set = self.client.query(query, bind_params=params, epoch='s')
        points = list(result_set.get_points())
        if not points:
            dt = datetime.datetime.min
        else:
            dt = datetime.datetime.fromtimestamp(points[0]['time'])
        return dt

    def read_records(self, prober_name, dst_ip, start_time, end_time) -> List:
        """ Return the list of records from start to end times, inclusive.

            start_time and end_time are datetime.datetime objects.
            If there are no records within the time range, [] is returned.

            Sample return:
                [{'1970-01-01T12:34:56}, 0.0123}, {...}, ...]
        """
        if not self.client:
            self._connect()
        start_time = str(int(start_time.timestamp()))
        end_time = str(int(end_time.timestamp()))
        query = 'SELECT "latency" FROM "icmp-echo" WHERE prober_name=$prober_name AND ' + \
                'dst_ip=$dst_ip AND time>=' + start_time + 's AND time<=' + end_time + 's'
        params = {
            'prober_name': prober_name,
            'dst_ip': dst_ip,
        }
        logging.debug("Querying: %s | %s", query, params)
        result_set = self.client.query(query, bind_params=params, epoch='s')
        points = list(result_set.get_points())
        logging.debug("Got %i records from %i to %i", len(points), start_time, end_time)
        return points
