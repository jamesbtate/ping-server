#!/usr/bin/env python3
"""
Database abstraction layer
"""

from abc import ABC, abstractmethod
from functools import lru_cache
import time


class Database(ABC):
    def __init__(self):
        super().__init__()

    @staticmethod
    def seconds_to_short_latency(seconds):
        """ Converts difference in times to a short integer latency.

        seconds - time in seconds
        If either parameter is null, a timeout is assumed.

        Used to store latency values of 0-1 seconds in a 2-byte field.
        0.0s => 0, 0.01s => 655, 0.5s => 32767
        None => 65535 (the magic value for timeout)
        1.00001s => 65535 (>1.0s also considered a timeout)

        Returns an integer in [0,65535]. A short integer or simply "short."
        """
        if seconds is None:
            return 65535
        short_latency = round(seconds * 65534)  # int in 0..65534
        if short_latency > 65535 or short_latency < 0:
            short_latency = 65535  # treat >1000ms replies as timeouts
        return short_latency


    @staticmethod
    def time_diff_to_short_latency(start, stop):
        """ Converts difference in times to a short integer latency.

        start - Start time in seconds
        stop - Stop time in seconds
        If either parameter is null, a timeout is assumed.

        Used to store latency values of 0-1 seconds in a 2-byte field.
        0.0s => 0, 0.01s => 655, 0.5s => 32767
        None => 65535 (the magic value for timeout)
        1.00001s => 65535 (>1.0s also considered a timeout)

        Returns an integer in [0,65535]. A short integer or simply "short."
        """
        if start is None or stop is None:
            short_latency = 65535  # magic value in the not null column
        else:
            seconds = stop - start
            short_latency = Database.seconds_to_short_latency(seconds)
        return short_latency

    @staticmethod
    @lru_cache(maxsize=65536)
    def short_latency_to_seconds(short):
        """ Converts an unsigned short [0,65535] to float in [0.0,1.0] or None

        short - unsigned integer in [0,65535]

        Used to store latency values of 0-1 seconds in a 2-byte field.
        0 => 0.0, 655 => 0.01, 32767 => 0.5
        65535 => None (the magic value for timeout)
        Any other value of input throws an exception.

        Returns a float in [0.0,1.0] or None.
        """
        if type(short) is not int:
            raise TypeError("Argument must be an integer in [0,65535]")
        if short == 65535:
            return None
        if short < 0 or short > 65535:
            raise ValueError("Argument must be an integer in [0,65535]")
        return short / 65534.0

    @abstractmethod
    def src_dst_id(self, src, dst):
        pass

    @abstractmethod
    def get_src_dst_pairs(self):
        pass

    @abstractmethod
    def get_src_dst_by_id(self, id):
        pass

    @abstractmethod
    def get_poll_counts_by_pair(self, src_ip, dst_ip):
        pass

    @abstractmethod
    def get_poll_data_by_id(self, pair_id, start=None, stop=None):
        pass

    @abstractmethod
    def record_poll_data(self, src_ip, dst_ip, send_time, receive_time):
        pass
