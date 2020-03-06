# Binary File Formats Documentation

This document describes the different versions of the proprietary database
files.

### Justification - Why do you need your own database format?
I didn't put a lot of time into finding a suitable database format/library.
I did, however spend substantial time trying to get rrdtool to work.
Unfortunately, it seems the interpolation "feature" of rrdtool cannot be
disabled. For an application such as this, we don't want any interpolation,
or we at least want the option of disabling it, in the event data points are
missed for whatever reason.

### Version 2
This version was only used in preliminary tests to measure the performance
of a proprietary binary file for reading and writing latency measurements.
This version is called version just because the fifth byte is a 2, and the
fifth byte is used as the version number in subsequent versions/formats.
```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|       P       |       I       |       N       |       G       |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|     0x02      |       I       |    B or H     |     data...   |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+               |
|                            .......                            |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```
The first four bytes are the magic value `PING` in ASCII. The next byte is a 2
in one's complement, specifying the length of the struct format specifier. The
following two bytes are the struct format specifier in ASCII. The struct
format specifier is the exact format used by the Python `struct` module.
The first byte specifies the type for the first field of a record, the epoch
time (4-byte unsigned integer). The second byte specifies the type for the
latency measurement - B is 1-byte unsigned integer and H is 2-byte unsigned
integer.

The endian-ness is not specified. It is presumed to be little-endian as is
traditional in x86 computers.

### Version 3
This is the first version that is intended for actual use. The header
notably has additional fields to handle the rolling-over of the data within
the file. This version does not specify a maximum number of records. That
task is left to the writing software. All numeric values are little-endian
and sizes are standard sizes. See [Struct format characters].
```
      0                   1                   2                   3
bit:  0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
byte +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
0    |       P       |       I       |       N       |       G       |
     +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
4    |    version    |  data_length  |            unused             | 
     +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+           
8    |                                                               |
     +                            offset                             +
12   |                                                               |
     +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
16   |                                                               |
     +                       number_of_records                       +
20   |                                                               |
     +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
24   |                           records...                          |
     +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```
- Magic number: 32 bits

   This is the file signature. It is the ASCII string "PING"

- version: 8 bits

   The version of the database file. This is an unsigned byte
   (8-bit integer). Here we are version 3 so the value is 0x03.

- data_length: 8 bits

   The length of the measurement field in bytes. Given as an unsigned byte.
   Typically 0x02.

- unused: 16 bits

   These two bytes are unused in the current specification. They are
   padding so the following large fields fall on word boundaries.

- offset: 64 bits

   This is an unsigned long (8 bytes) that indicates the byte offset of
   the first data record in the file chronologically. Initially, this would
   be 24 (0x00000018) to point to the first data record in the file. Once
   the file starts to rollover, it will no longer point to the absolute
   first record of the file. This field should be updated on every write,
   although the value will not change until the file fills up.

- number_of_records: 64 bits

   This is an unsigned long (8 bytes) that contains the number of data
   records in the file. The file may be allocated to occupy more space than
   the number of records it currently contains. This field should be updated
   on every write.

- records:

   The data records immediately follow the *number_of_records* field. Each
   record is an unsigned int (4 bytes) for the time of the measurement and
   *data_length* bytes for the measurement at that time. Gaps are not left
   in the records for absent measurements, whether intentionally skipped
   or missing. Records are typically 6 bytes, determined by 4 + *data_length*.

[Struct format characters]: https://docs.python.org/2/library/struct.html#format-characters