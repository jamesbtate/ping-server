# Ping Server

A distributed application for running constant pings against hosts and logging the results. Used for network and system monitoring. Probes can be run on multiple systems with results stored on the master for testing from multiple locations.

# Production Setup
This project now supports docker-compose. These steps create one prober along with the
collector, databases, webapp, and nginx containers.

1. Start containers detached: `docker-compose up -d`
2. Configure the prober:
   1. Visit the Configure tab of the web interface (http://localhost:8080)
   2. Add a prober with name `prober1` and key `prober1`.
   3. Add one or more targets.
   4. Create a probe group that includes the prober and one or more targets.

## Teardown
1. `docker-compose down`


# Development Environment Setup
Development is very similar to prod. There is a separate development container/image
named `web-dev` in `Dockerfile`. This container listens on TCP/8000 using the
Django development web server and it has a bind mount for the application code. With
those two pieces, changes to code files are immediately reflected.

1. Follow production steps above to setup most of the environment.
2. `docker-compose up web-dev` to start the web development container as well.
3. Visit http://localhost:8000 instead to see the development site. The production
version is still running on port 8080.

## Pre-requisites:

- Recent docker-compose that supports "profiles."
- Most recently tested with Docker desktop on Windows 10 and Docker/docker-compose on
CentOS 8.
- Previously used with the Docker in CentOS 7 extras repo, but that version of
docker-compose is too old to support profiles. Probably the bits about profiles could
just be removed from `docker-compose.yml` then it would work (with unnecessary extra
containers).


## Sources

Some code related to ICMP from Python taken from
[PyPing](https://github.com/Akhavi/pyping)

## License

This project uses GPLv2. See LICENSE.
