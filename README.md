# Ping Server

A distributed application for running constant pings against hosts and logging the results. Used for network and system monitoring. Probes can be run on multiple systems with results stored on the master for testing from multiple locations.

## Usage
1. Create a database and user for the ping recorder.
    ```
    create database ping
    create user ping@localhost identified by 'abcd1234'
    grant all on ping.* to ping@localhost
    flush privileges
    ```
2. Import the database schema (only on the server).
  1. mysql *database* < schema.sql
1. Copy `default.conf` to `ping.conf` and modify as needed.
  1. Fill in the database details in the `server` section.
2. Run the server process with ./server.py
3. Run the ping process with ./probe.py
  1. Remember that you must generally be root to use raw ICMP sockets.

## Sources

Some code taken from [PyPing](https://github.com/Akhavi/pyping)

## License

This project uses GPLv2. See LICENSE.
