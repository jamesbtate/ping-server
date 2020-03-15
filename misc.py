"""
Misc functions
"""

import argparse
import logging
import time
import re

def is_number(x):
    """ Returns true if the parameter is an integer or float. """
    return type(x) is float or type(x) is int


def duration_string_to_seconds(duration):
    """ Calculates the number of seconds in a duration string.

        Argument is a shorthand duration string e.g. 1h or 2d or 57m

        Calculation is not calendar-specific e.g. 1d always equals 86400
        seconds.

        Returns an integer number of seconds.

        Raises TypeError and ValueError as appropriate.
    """
    letters_to_seconds = {
        's': 1,
        'm': 60,
        'h': 3600,
        'd': 86400,
        'w': 86400 * 7,
        'n': 86400 * 30,
        'y': 86400 * 365
    }
    if type(duration) is not str:
        raise TypeError("duration must be string")
    matches = re.findall("(\d+)(.)", duration)
    if not matches:
        raise ValueError("Invalid duration string")
    seconds = 0
    for match in matches:
        multiplier = int(match[0])
        letter = match[1].lower()
        if letter not in letters_to_seconds:
            raise ValueError("Invalid duration letter in string")
        seconds += multiplier * letters_to_seconds[letter]
    return seconds


def get_time_extents(args, default=3601):
    """ Return start and stop UNIX time integers from a request arguments.

        The argument 'args' is a werkzeug MultiDict containing HTTP query
        arguments/parameters. Some keys are used to determine the time
        bounds.

        If suitable dictionary keys are not found, a time window ending now
        is returned. The kwarg 'default' specifies how many seconds long
        that time window is.

        Returns:
            start_time  # start of time window/extents (integer)
            stop_time   # end of time window/extents (integer)
    """
    start_time = args.get('start_time', default=None, type=int)
    stop_time = args.get('stop_time', default=None, type=int)
    window = args.get('window', default=None)
    if window:
        stop_time = int(time.time())
        try:
            seconds = duration_string_to_seconds(window)
        except ValueError:
            seconds = default
        start_time = stop_time - seconds
    else:
        if not start_time and not stop_time:
            stop_time = int(time.time())
            start_time = stop_time - default
        elif not start_time:
            start_time = stop_time - default
        elif not stop_time:
            stop_time = start_time + default
    return start_time, stop_time


def make_generic_parser(description):
    """ Make and return an argparse ArgumentParser with common options """
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('-c', '--config-file', default='ping.conf',
                        help="Path to config file. Default is ./ping.conf")
    parser.add_argument('-f', '--foreground', action='store_true',
                        help="Run in foreground and log to stderr.")
    parser.add_argument('-d', '--debug', dest='log_level',
                        default=logging.INFO, action='store_const',
                        const=logging.DEBUG,
                        help="Enable debug-level logging.")
    return parser
