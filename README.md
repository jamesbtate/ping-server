# Ping Server

A distributed application for running constant pings against hosts and logging the results. Used for network and system monitoring. Probes can be run on multiple systems with results stored on the master for testing from multiple locations.

## Setup
1. Make some directories:
  1. `mkdir /opt/ping`
  2. `mkdir /opt/ping/influxdb`
2. Create docker network
  1. `docker network create ping`
3. Create ping user
  1. `useradd -d /opt/ping ping`
4. Directory permissions
  1. `chown -R ping:ping /opt/ping`
5. Setup user/group mapping. Skipping this for now and just running as root.
  1. Modify /etc/subuid and /etc/subgid
  2. Modify /etc/docker/daemon.json to remap the users. This has implications for other containers on the system.
6. Create container
  1. `docker create --name ping_influxdb -p 8086:8086 -v /opt/ping/influxdb/:/var/lib/influxdb influxdb`
7. Start container
  1. `docker start ping_influxdb`
8. Build docker images. This will take a while the first time (mostly C and C++ compilation of numpy and matplotlib)
  1. `./docker_build.bash`


## Old Usage
1. Create a database and user for the ping recorder.
    ```
    create database ping;
    create user ping@localhost identified by 'abcd1234';
    grant all on ping.* to ping@localhost;
    flush privileges;
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
