"""
Wrapper for a binary data file containing a log of ping results.
A DatabaseBinary object will keep a list/mapping of multiple Datafile objects.
"""

import struct


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
        self.record_struct = struct.Struct('IH')
        self.data_length = data_length
        self.offset = offset
        self.number_of_records = number_of_records
        self.max_records = max_records
        self.max_data_area_bytes = (4 + data_length) * max_records

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

    def record_datum(self, epoch, value):
        """ Add an entry to the data file at the end of the data set.

            Writes the data to the the file and updates the header values:
            number_of_records and offset (if needed).

            Arguments:
            epoch: UNIX time in seconds (integer)
            value: latency value
        """
        seek_to = self.offset + self.number_of_records * (4 + self.data_length)
        if seek_to >= self.header_struct.size + self.max_data_area_bytes:
            seek_to -= self.max_data_area_bytes
        self.file.seek(seek_to)
        self.file.write(self.record_struct.pack(epoch, value))
        if self.number_of_records < self.max_records:
            self.number_of_records += 1
            self.write_number_of_records()
        else:
            self.offset += 4 + self.data_length
            self.write_offset()
