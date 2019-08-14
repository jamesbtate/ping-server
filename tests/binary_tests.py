#!/usr/bin/env python3
import argparse
import datetime
import logging
import struct
import random
import time


def parse_args():
    description = "Test reading and writing binary files"
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('-w', '--write', action='store_true',
                        help='Test writing binary file.')
    parser.add_argument('-r', '--read', action='store_true',
                        help='Test reading binary file.')
    parser.add_argument('-n', '--number', type=int, default=86400,
                        help='Number of items to write to file.')
    parser.add_argument('-f', '--filename', default='binary.data',
                        help='Path to test file')
    parser.add_argument('-m', '--minimum', type=int, default=0,
                        help='Random minimum')
    parser.add_argument('-M', '--maximum', type=int, default=255,
                        help='Random maximum')
    parser.add_argument('-b', '--read-blocks', metavar='block-size', type=int,
                        help='Read file, specify number of records in a block to read at a time.')
    args = parser.parse_args()
    if not args.read and not args.write and not args.read_blocks:
        parser.error("No test specified.")
    return args


def test_write_args(args):
    test_write(args.filename, args.number, args.minimum, args.maximum)


def test_write(filename, number, minimum, maximum):
    struct_format = 'IB'
    if minimum > 255 or maximum > 255:
        struct_format = 'IH'
    header = 'PING\x02' + struct_format
    # file header is 'PING' plus 1 byte specifying length of struct format
    # of each record, which immediately follows the first 5 bytes.
    f = open(filename, 'wb')
    f.write(header.encode('utf-8'))
    now = int(time.time())
    for i in range(number):
        d = struct.pack(struct_format, now + i,
                        random.randint(minimum, maximum))
        _ = f.write(d)
    f.close()


def test_read_args(args):
        test_read(args.filename)


def test_read(filename):
    start = time.time()
    f = open(filename, 'rb')
    header = f.read(5)
    format_size = header[4]
    format_string = f.read(format_size).decode('utf-8')
    record_size = struct.calcsize(format_string)
    logging.info("Read header from binary file %s", filename)
    logging.info("Format length: %i  Format: %s  Record length: %i",
                 format_size, format_string, record_size)
    count = 0
    while True:
        data = f.read(record_size)
        if not data:
            break
        values = struct.unpack(format_string, data)
        count += 1
    stop = time.time()
    logging.info("Read %s log messages in %.3f seconds", count, stop - start)
    logging.info("Last values: time:%i latency:%i", values[0], values[1])
    f.close()


def test_read_n_records(filename, n):
    """ Test reading files in blocks of n records. """
    record_size = 6
    logging.info("Record size: %i", record_size)
    record_struct = struct.Struct("IH")
    logging.info("Record struct length: %i", record_struct.size)
    record_struct_1000 = struct.Struct("=" + "IH" * 1000)
    logging.info("Record struct 1000 length: %i", record_struct_1000.size)
    start = time.time()
    f = open(filename, 'rb')
    count = 0
    all_values = []
    while True:
        data = f.read(record_size * n)
        if not data:
            break
        if len(data) == record_size * 1000:
            values_list = record_struct_1000.unpack(data)
            for i in range(0, len(values_list), 2):
                all_values.append([values_list[i], values_list[i+1]])
            count += 1000
        else:
            for i in range(0, len(data), record_size):
                if i + record_size > len(data):
                    break
                values = record_struct.unpack(data[i:i+record_size])
                all_values.append([values[0], values[1]])
                count += 1
    for record in all_values:
        record[0] = datetime.datetime.fromtimestamp(record[0])
    stop = time.time()
    logging.info("Read %i (%i) records in %.3f seconds",
                 count, len(all_values), stop - start)
    logging.info("Last values: time:%i latency:%i", values[0], values[1])
    f.close()


def main():
    args = parse_args()
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    if args.write:
        test_write_args(args)
    if args.read:
        test_read(args.filename)
    if args.read_blocks:
        test_read_n_records(args.filename, args.read_blocks)


if __name__ == '__main__':
    main()

