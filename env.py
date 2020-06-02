"""
Module for retrieving environment variables or their default values
"""

import logging
import os


DEFAULTS = {
    'DEBUG': 1,
    'SECRET_KEY': 'pingpingpingpingpingpingpingpingpingpingpingpingpi',
    'ALLOWED_HOSTS': '*',
    'DB_HOST': 'ping_mariadb',
    'DB_DB': 'ping',
    'DB_USER': 'ping',
    'DB_PASS': 'ping',
    'DB_PORT': '3306',
    'INFLUXDB_HOST': 'ping_influxdb',
    'INFLUXDB_DB': 'ping',
    'INFLUXDB_USER': 'influxdb',
    'INFLUXDB_PASS': 'influxdb',
    'INFLUXDB_PORT': '8086',
}


def get_env_string(name):
    """ Return the environment variable with the given name or the default value if not set."""
    if name in os.environ:
        logging.debug('Found environment variable %s: %s', name, os.environ[name])
        return os.environ[name]
    if name in DEFAULTS:
        logging.debug('Using default environment variable %s: %s', name, DEFAULTS[name])
        return DEFAULTS[name]
    raise KeyError(f"No environment variable or default value for key {name}")


def get_env_boolean(name):
    """ Return True or False for a given environment variable or default value. """
    return bool(get_env_string(name))


def get_influxdb_params():
    """ Return a dictionary of parameters to use to connect to InfluxDB """
    db_params = {
        'INFLUXDB_HOST': get_env_string('INFLUXDB_HOST'),
        'INFLUXDB_DB': get_env_string('INFLUXDB_DB'),
        'INFLUXDB_USER': get_env_string('INFLUXDB_USER'),
        'INFLUXDB_PASS': get_env_string('INFLUXDB_PASS'),
        'INFLUXDB_PORT': int(get_env_string('INFLUXDB_PORT')),
    }
    return db_params
