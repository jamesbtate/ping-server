"""
Wrapper for a binary data file containing a log of ping results.
A DatabaseBinary object will keep a list/mapping of multiple Datafile objects.
"""

import struct
import logging
from database import Database

class Datafile(object):
    """ This class will be a factory.

        See file format documentation in file_formats.md.
    """
    DEFAULT_VERSION = 3
    DEFAULT_DATA_LENGTH = 2
    DEFAULT_OFFSET = 24
    DEFAULT_NUMBER_OF_RECORDS = 0
    DEFAULT_MAX_RECORDS = 86400 * 7
    STRUCT_U_8 = struct.Struct('Q')

    def __init__(self, pid, path, version, data_length, offset,
                 number_of_records, max_records):
        """ This constructor should not be used outside the factory. """
        self.pid = pid  # database ID of the src-dst pair
        self.path = path  # path to data file on disk
        self.file = None  # file handle
        self.version = version
        self.header_struct = struct.Struct('ccccBBxxQQ')
        self.header_length = self.header_struct.size
        self.record_struct = struct.Struct('IH')
        self.record_length = self.record_struct.size
        self.data_length = data_length
        self.offset = offset
        self.number_of_records = number_of_records
        self.max_records = max_records
        self.max_data_area_bytes = (4 + data_length) * max_records
        self.max_file_bytes = self.max_data_area_bytes + self.header_length

    def open_file(self, mode):
        """ Open the underlying file using the given mode. """
        self.file = open(self.path, mode)

    @staticmethod
    def create_new_datafile(pid, path,
                            version=DEFAULT_VERSION,
                            data_length=DEFAULT_DATA_LENGTH,
                            offset=DEFAULT_OFFSET,
                            number_of_records=DEFAULT_NUMBER_OF_RECORDS,
                            max_records=DEFAULT_MAX_RECORDS):
        df = Datafile(pid, path, version, data_length, offset,
                      number_of_records, max_records)
        df.open_file('w+b')  # w+b means binary; truncate any existing file
        df.write_header()
        return df

    @staticmethod
    def open_datafile(pid, path,
                      version=DEFAULT_VERSION,
                      data_length=DEFAULT_DATA_LENGTH,
                      offset=DEFAULT_OFFSET,
                      number_of_records=DEFAULT_NUMBER_OF_RECORDS,
                      max_records=DEFAULT_MAX_RECORDS):
        df = Datafile(pid, path, version, data_length, offset,
                      number_of_records, max_records)
        df.open_file('r+b')  # r+b means binary; do not truncate file
        df.read_header()
        return df

    def read_header(self):
        header_bytes = self.file.read(self.header_struct.size)
        header = self.header_struct.unpack(header_bytes)
        self.version = header[4]
        self.data_length = header[5]
        self.offset = header[6]
        self.number_of_records = header[7]

    def write_header(self):
        """ Write the entire data file header to the top of the data file. """
        header = self.header_struct.pack(b'P', b'I', b'N', b'G',
                                         self.version, self.data_length,
                                         self.offset,
                                         self.number_of_records)
        self.file.seek(0)
        self.file.write(header)

    def write_offset(self):
        """ Update the header with the current offset. """
        self.file.seek(8)
        self.file.write(Datafile.STRUCT_U_8.pack(self.offset))

    def write_number_of_records(self):
        """ Update the header with the current number of records. """
        self.file.seek(16)
        self.file.write(Datafile.STRUCT_U_8.pack(self.number_of_records))

    def record_datum(self, datum_time, send_time, receive_time):
        """ Add an entry to the data file at the end of the data set.

            Writes the data to the the file and updates the header values:
            number_of_records and offset (if needed).

            Arguments:
            datum_time: UNIX time in seconds (integer)
            send_time: precise time ping was sent (float)
            receive_time: precise time ping was received (float)
        """
        seek_to = self.offset + self.number_of_records * (4 + self.data_length)
        if seek_to >= self.header_struct.size + self.max_data_area_bytes:
            seek_to -= self.max_data_area_bytes
        self.file.seek(seek_to)
        encoded_latency = Database.time_diff_to_short_latency(send_time,
                                                              receive_time)
        self.file.write(self.record_struct.pack(datum_time, encoded_latency))
        if self.number_of_records < self.max_records:
            self.number_of_records += 1
            self.write_number_of_records()
        else:
            self.offset += 4 + self.data_length
            self.write_offset()

    def read_record(self):
        """ Read a data record at the current position in the file.

            Decodes the stored data.
        """
        record_bytes = self.file.read(self.record_length)
        record = self.record_struct.unpack(record_bytes)
        latency = Database.short_latency_to_seconds(record[1])
        return [record[0], latency]

    def read_all_records(self):
        records = []
        self.file.seek(self.offset)
        for i in range(self.number_of_records):
            if self.file.tell() >= self.max_file_bytes:
                self.file.seek(self.header_length)
            record = self.read_record()
            records.append(record)
        logging.debug("Read %i records from %s", len(records), self.file.name)
        return records

    def read_records(self, start_time, end_time):
        """ Return the list of records from start to end times, inclusive.

            start_time and end_time are UNIX epoch seconds.
            If there are no records within the time range, [] is returned.

            Sample return:
                [(epoch-integer, 123), (epoch-integer+1, 65534), ...]
        """
        records = self.read_all_records()
        if records[0][0] > end_time:
            logging.debug("First record was after end_time: %i", end_time)
            return []
        if records[-1][0] < start_time:
            logging.debug("Last record was before start_time: %i", start_time)
            return []
        # if we get to this point, we will always return at least one record.
        # don't bother with binary search for now
        first = 0
        for i in range(len(records)):
            if records[i][0] >= start_time:
                first = i
                break
        last = len(records)
        for i in range(first + 1, len(records)):
            if records[i][0] > end_time:
                last = i - 1
                break
        specific_records = records[first:last]
        logging.debug("Got %i specific records from %i to %i",
                      len(specific_records), start_time, end_time)
        return specific_records
