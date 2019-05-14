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

### Version 0.1
This version was only used in preliminary tests to measure the performance
of a proprietary binary file for reading and writing latency measurements. 
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

### Version 1.0
This is the first version that is intended for actual use. The header
notably has additional fields to handle the rolling-over of the data within
the file. 
```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|       P       |       I       |       N       |       G       |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|    Version    |               |               |               |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                            .......                            |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```