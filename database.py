#!/usr/bin/python3
"""
Database abstraction layer
"""

from abc import ABC, abstractmethod


class Database(ABC):
    def __init__(self):
        super().__init__()

    @abstractmethod
    def get_src_dst_pairs(self):
        pass
