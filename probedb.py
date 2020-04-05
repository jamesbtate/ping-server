#!/usr/bin/env python3
"""
Database abstraction layer for prober and a CLI tool for management of the prober's DB.
"""

from typing import List
import argparse
import logging
import sqlite3
import sys


DEFAULT_DB_PATH: str = './prober_db.sqlite3'


class ProberDatabase(object):
    """ Abstraction layer for the prober SQLite3 DB. """

    def __init__(self, db_file_path: str = DEFAULT_DB_PATH):
        self.db_file_path: str = db_file_path
        self.connection: sqlite3.Connection = sqlite3.connect(self.db_file_path)
        self.cursor: sqlite3.Cursor = self.connection.cursor()
        if 'target' not in self.get_tables():
            logging.warning("Database (%s) empty. Initializing...", self.db_file_path)
            self.init_db()

    def execute(self, query: str) -> None:
        self.cursor.execute(query)

    def execute_commit(self, query: str) -> None:
        self.cursor.execute(query)
        self.connection.commit()

    def execute_fetch_all(self, query: str) -> List[tuple]:
        """ Executes the query and returns the output of cursor.fetchall()

        :return: a list (will be empty if there were no rows)
        """
        self.execute(query)
        return self.cursor.fetchall()

    def get_tables(self) -> List[str]:
        """ Get a list of table names in the database.

        :return: a list of strings
        """
        query = "select name from sqlite_master where type='table'"
        results = self.execute_fetch_all(query)
        return [_[0] for _ in results]

    def init_db(self) -> None:
        """ Initialize the database i.e. create the tables

        :return: None
        """
        query = """create table target (
                   id integer primary key autoincrement,
                   name text,
                   ip text,
                   port integer,
                   type text,
                   date_added text,
                   enabled boolean
                   )"""
        self.execute_commit(query)

    def get_targets(self) -> List[tuple]:
        """ Returns a list of all the targets in the database. """
        query = "select * from target"
        return self.execute_fetch_all(query)


def parse_args(raw_args: List[str] = sys.argv[1:]) -> argparse.Namespace:
    """ Setup the argument parser and parse the args.

    Optionally pass in the raw arguments instead of using sys.argv.
    :return: the output of argument_parser.parse_args()
    """
    description = "CLI tool for management of the prober's database."
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('db_file', nargs='?', default=DEFAULT_DB_PATH,
                        help="Path to SQLite3 prober database file.")
    args = parser.parse_args(raw_args)
    return args


def main():
    args = parse_args()
    db = ProberDatabase(db_file_path=args.db_file)


if __name__ == '__main__':
    main()