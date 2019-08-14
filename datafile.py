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
        self.record_format = 'IH'
        self.record_struct = struct.Struct('=' + self.record_format)
        self.multiple_record_structs = {1: self.record_struct}
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
        logging.info("Created new datafile: %i %s", pid, path)
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

    def _write_record_now(self, datum_time, encoded_latency):
        """ Writes one record to the datafile immediately.

            No seeking is done. No other fields are updated.

            Args:
            datum_time: UNIX time (integer)
            encoded_latency: integer 0..65535 representing latency in 0.0..1.0s
        """
        self.file.write(self.record_struct.pack(datum_time, encoded_latency))

    def record_datum(self, datum_time, send_time, receive_time):
        """ Add an entry to the data file at the end of the data set.

            Writes the data to the the file and updates the header values:
            number_of_records and offset (if needed).

            Arguments:
            datum_time: UNIX time in seconds (integer)
            send_time: precise time ping was sent (float)
            receive_time: precise time ping was received (float)
        """
        seek_to = self.offset + self.number_of_records * self.record_length
        if seek_to >= self.max_file_bytes:
            seek_to -= self.max_data_area_bytes
        self.file.seek(seek_to)
        encoded_latency = Database.time_diff_to_short_latency(send_time,
                                                              receive_time)
        self._write_record_now(datum_time, encoded_latency)
        if self.number_of_records < self.max_records:
            self.number_of_records += 1
            self.write_number_of_records()
            #if self.number_of_records % 10 == 0:
            #    self.file.flush()
        else:
            self.offset += self.record_length
            if self.offset >= self.max_file_bytes:
                self.offset -= self.max_data_area_bytes
            self.write_offset()
            #if (self.offset - self.header_length) % (self.record_length * 10) == 0:
        self.file.flush()
        logging.debug("Recorded datum for PID %i: %i %i Num: %i Offset: %i",
                      self.pid, datum_time, encoded_latency,
                      self.number_of_records, self.offset)

    def write_all_records(self, records):
        """ Used to overwrite all records in the datafile.

            Records are overwritten starting after the header.
            number_of_records is updated. offset is set to header_length.
        """
        self.offset = self.header_length
        self.file.seek(self.offset)
        for record in records:
            encoded_latency = Database.seconds_to_short_latency(record[1])
            self._write_record_now(record[0], encoded_latency)
        self.number_of_records = len(records)
        self.write_number_of_records()
        self.write_offset()

    def read_record(self):
        """ Read a data record at the current position in the file.

            Decodes the stored data.
        """
        record_bytes = self.file.read(self.record_length)
        record = self.record_struct.unpack(record_bytes)
        latency = Database.short_latency_to_seconds(record[1])
        return [record[0], latency]

    def get_multiple_record_struct(self, n):
        """ Get (make if needed) to decode n records at once. """
        try:
            return self.multiple_record_structs[n]
        except KeyError:
            new_record_struct = struct.Struct('=' + self.record_format * n)
            self.multiple_record_structs[n] = new_record_struct
            return new_record_struct

    def read_n_records(self, n):
        """ Read multiple records at the current position in the file.

            Returns a list of lists: one sublist for each decoded record
        """
        records = []
        data = self.file.read(self.record_length * n)
        if not data:
            return records
        records_read = len(data) // self.record_length
        if len(data) % self.record_length != 0:
            logging.warning("Read %i bytes not divisible by record length: %i",
                            len(data), self.record_length)
        if records_read != n:
            logging.warning("Read fewer bytes than expected: %i/%i",
                            len(data), n * self.record_length)
        read_struct = self.get_multiple_record_struct(len(data) //
                                                      self.record_length)
        all_values = read_struct.unpack(data)
        for i in range(records_read):
            epoch = all_values[i * 2]
            latency = Database.short_latency_to_seconds(all_values[i * 2 + 1])
            records.append([epoch, latency])
        return records

    def read_all_records(self):
        all_records = []
        self.file.seek(self.offset)
        remaining_records = self.number_of_records
        while True:
            pos = self.file.tell()
            #if pos >= self.max_file_bytes:
            current_file_length = self.number_of_records * self.record_length \
                                  + self.header_length
            if pos >= current_file_length:
                self.file.seek(self.header_length)
                pos = self.header_length
            bytes_left_to_eof = current_file_length - pos
            records_left_to_eof = bytes_left_to_eof // self.record_length
            read = min(1000, records_left_to_eof, remaining_records)
            records = self.read_n_records(read)
            all_records += records
            remaining_records -= len(records)
            if remaining_records <= 0:
                break
        logging.debug("Read %i records from %s", len(records), self.file.name)
        return all_records

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
