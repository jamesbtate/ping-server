# Ping Server

A distributed application for running constant pings against hosts and logging the results. Used for network and system monitoring. Probes can be run on multiple systems with results stored on the master for testing from multiple locations.

# Production Setup

## Simplified Setup
1. `./docker_build_new.bash`
   1. Above command uses multi-stage builds. It requires docker 17.something.
   2. Or use this command with an older docker version. It uses the individual Dockerfile-*thing* files: `./docker_build_old.bash`
1. `./docker_create.bash`
1. `./docker_start.bash`

## Simplified Cleanup
1. `./docker_rm.bash`   # This kills the containers if they are running.
1. `./docker_image_rm.bash`   # This deletes the images.

## Setup Details
0. `./initial_setup.bash` or do the next few steps manually.
1. Make some directories:
   1. `mkdir /opt/ping`
   2. `mkdir /opt/ping/influxdb`
   2. `mkdir /opt/ping/mariadb`
2. Create docker network
   1. `docker network create ping`
3. Create ping user
   1. `useradd -d /opt/ping ping`
4. Directory permissions
   1. `chown -R ping:ping /opt/ping`
5. Setup user/group mapping. Skipping this for now and just running as root.
   1. Modify /etc/subuid and /etc/subgid
   2. Modify /etc/docker/daemon.json to remap the users. This has implications for other containers on the system.
0. Create config files.
   1. Copy `default.conf` to `ping.conf`
   1. Copy `config.default.py` to `config.py`
   2. Modify values as necessary. If you change database stuff, you need to re-run `docker_build_X.bash` too.
0. Add prober to database
   1. `mysql -h 127.0.0.1 -P 13306 -u ping -pping ping`
   1. ```INSERT INTO prober (`name`,`key`,`added`) VALUES ('prober1', 'prober1', NOW());```
8. Build docker images. This will take a minute or two. A couple things need to compile.
   1. `./docker_build_new.bash`   # This requires docker 17.05+
   (does not work on RHEL7-based distributions. Use podman instead.)
6. Create containers
   1. `./docker_create.bash`
7. Start containers
   1. `./docker_start.bash`



# Development Environment Setup

## Pre-requisites:

- Only tested on Linux
- Python3.6+
- RHEL-compatible package names:
  - python3
  - mariadb-devel
  - gcc
  - docker *or* podman
  - probably a bunch more things
- Run a MySQL-comaptible database and InfluxDB.
  - These can easily be containers even if the application is not containerized.
  - Look in `docker_create.bash` to see example MariaDB and InfluxDB containers.
- Make a virtuenenv:
  - `./make_venv.bash`
    - This script makes the venv, activates it, and installs the requirements.
- Copy `config.default.py` to `config_local.py` and set values accordingly.
- Copy `default.conf` to `dev.py` and set values accordingly.
- Apply Django migrations:
  - `./manage.py migrate`
- Run collector:
  - `DJANGO_SETTINGS_MODULE=pingweb.settings_dev ./server.py -fdc dev_local.conf`
- Run prober:
  - `./probe.py -fdc dev.conf`
- Run Django development webserver:
  - `DJANGO_SETTINGS_MODULE=pingweb.settings_dev ./manage.py runserver 0.0.0.0:5001`

## Some old development environment execution instructions
1. Create a database and user for the ping recorder.
    ```
    create database ping;
    create user ping@localhost identified by 'ping';
    grant all on ping.* to ping@localhost;
    flush privileges;
    ```
2. Import the database schema (only on the server).
  1. mysql *database_name* < schema.sql
1. Copy `default.conf` to `ping.conf` and modify as needed.
  1. Fill in the database details in the `server` section.
2. Run the server process with ./server.py
3. Run the ping process with ./probe.py
  1. Remember that you must generally be root to use raw ICMP sockets.

 You can connect to the MySQL service from the host with `mysql -h 127.0.0.1 -P 13306 -pping`.

## Sources

Some code taken from [PyPing](https://github.com/Akhavi/pyping)

## License

This project uses GPLv2. See LICENSE.
