#!/usr/bin/env python3
"""
Management tool for viewing and maybe modifying proprietary ping data files.
"""

from database_mysql import DatabaseMysql
from database_binary import DatabaseBinary
from server import read_config
from datafile import Datafile
import operator
import tabulate
import datetime
import argparse
import logging
import misc
import time
import os


def parse_args():
    description = "Run development webserver for ping project"
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('-d', '--debug', action='store_true',
                        help="Enable debug-level logging")
    parser.add_argument('-l', '--list', action='store_true', help="List datafiles")
    parser.add_argument('-i', '--info', action='store_true', help="Show datafile info")
    parser.add_argument('-H', '--head', action='store_true', help="Show first few records from datafile.")
    parser.add_argument('-T', '--tail', action='store_true', help="Show last few records from datafile.")
    parser.add_argument('-v', '--verify', action='store_true', help="Run some checks on the datafile.")
    parser.add_argument('-s', '--sort', action='store_true',
                        help="Read records from datafile and sort into output datafile.")
    parser.add_argument('datafile', nargs='?', help="Path to input datafile")
    parser.add_argument('-o', '--output', metavar="PATH", help="Output file.")
    args = parser.parse_args()
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    if args.debug:
        logger.setLevel(logging.DEBUG)

    if args.info or args.head or args.tail or args.sort:
        if not args.datafile:
            parser.error("Must specify input datafile")
    if args.sort and not args.output:
        parser.error("--sort requires --output")
    return args


def get_datafiles_and_mtimes(db):
    pairs = db.get_src_dst_pairs()
    for pair in pairs:
        try:
            pair['mtime'] = db.get_file_modification_time(pair['binary_file'],
                                                          iso8601=True)
        except FileNotFoundError:
            pair['mtime'] = "File not found"
        except PermissionError:
            pair['mtime'] = "Permission denied"
    return pairs


def list_datafiles(db):
    pairs = get_datafiles_and_mtimes(db)
    output = [["PID", "Datafile Path", "mtime"]]
    for pair in pairs:
        output.append([pair['id'], pair['binary_file'], pair['mtime']])
    print(tabulate.tabulate(output, headers='firstrow'))


def open_datafile(path):
    datafile = Datafile.open_datafile(-1, path)
    return datafile


def show_datafile_info(datafile):
    print("PID:", datafile.pid)
    print("Version:", datafile.version)
    print("Header Length:", datafile.header_length)
    print("Record Length:", datafile.record_length)
    print("Data Length:", datafile.data_length)
    print("Offset:", datafile.offset)
    print("Records:", datafile.number_of_records)
    print("Max Records:", datafile.max_records)
    print("Max Data Area Bytes:", datafile.max_data_area_bytes)
    print("Max File Bytes:", datafile.max_file_bytes)


def read_records(datafile):
    start = time.time()
    records = datafile.read_all_records()
    stop = time.time()
    logging.debug("Took %0.2f seconds to read all records", stop - start)
    return records


def show_datafile_records(records, start, stop):
    header = ['Index', 'UNIX Time', 'ISO Time', 'Latency (seconds)']
    output = []
    for i in range(start,stop):
        record = records[i]
        dt = datetime.datetime.fromtimestamp(record[0])
        human_time = dt.strftime('%Y-%m-%d_%H:%M:%S')
        output.append([i, record[0], human_time, record[1]])
    print(tabulate.tabulate(output, headers=header))


def show_datafile_head(records, num=10):
    show_datafile_records(records, 0, num)


def show_datafile_tail(records, num=10):
    show_datafile_records(records, len(records) - num, len(records))


def show_verify_datafile(datafile, records):
    # count how many time the records are out-of-order
    prev_record = records[0]
    decreases = 0
    for record in records:
        if record[0] < prev_record[0]:
            decreases += 1
        prev_record = record
    print("Number of records out of order:", decreases)


def sort_records_into_new_datafile(records, new_path):
    new_datafile = Datafile.create_new_datafile(-1, new_path)
    new_records = records[:]
    new_records.sort(key=operator.itemgetter(0))
    start = time.time()
    new_datafile.write_all_records(new_records)
    stop = time.time()
    logging.info("Wrote %i records to %s", len(records), new_path)
    logging.debug("Took %0.2f seconds to write all records", stop - start)


def main():
    args = parse_args()
    db_params = read_config()['server']
    db = DatabaseBinary(db_params)
    if args.list:
        list_datafiles(db)
    if args.datafile:
        datafile = open_datafile(args.datafile)
    if args.info:
        show_datafile_info(datafile)
    if args.head or args.tail or args.verify or args.sort:
        records = read_records(datafile)
        if args.head:
            show_datafile_head(records)
        if args.tail:
            show_datafile_tail(records)
        if args.verify:
            show_verify_datafile(datafile, records)
        if args.sort:
            sort_records_into_new_datafile(records, args.output)


if __name__ == '__main__':
    main()
