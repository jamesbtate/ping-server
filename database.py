#!/usr/bin/python3
"""
Database abstraction layer
"""

from abc import ABC, abstractmethod
import time


class Database(ABC):
    def __init__(self):
        super().__init__()

    @abstractmethod
    def get_src_dst_pairs(self):
        pass

    @abstractmethod
    def get_poll_counts_by_pair(self):
        pass

    @abstractmethod
    def get_poll_data_by_pair(self, pair_id,
                              start=time.time()-3600,
                              stop=time.time()):
        pass