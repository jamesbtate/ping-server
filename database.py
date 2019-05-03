#!/usr/bin/env python3
"""
Database abstraction layer
"""

from abc import ABC, abstractmethod
import time


class Database(ABC):
    def __init__(self):
        super().__init__()

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
            short_latency = round(seconds * 65534)  # int in 0..65534
            if short_latency > 65535 or short_latency < 0:
                short_latency = 65535  # treat >1000ms replies as timeouts
        return short_latency

    @abstractmethod
    def src_dst_id(self, src, dst):
        pass

    @abstractmethod
    def get_src_dst_pairs(self):
        pass

    @abstractmethod
    def get_poll_counts_by_pair(self):
        pass

    @abstractmethod
    def get_poll_data_by_pair(self, pair_id, start=None, stop=None):
        pass

    @abstractmethod
    def record_poll_data(self, src_ip, dst_ip, send_time, receive_time):
        pass
