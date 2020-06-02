"""
Module for retrieving configuration settings from the DB or the default values
"""

from pingweb.models import ServerSetting


DEFAULTS = {
    'ws_address': '0.0.0.0',
    'ws_port': '8765',
    'collector_log_file': 'collector.log',
    'web_address': '0.0.0.0',
    'web_port': '5000',
}


def get_setting_string(name):
    """ Return the configuration setting with the given name or the default value if not set."""
    try:
        setting = ServerSetting.objects.get(name=name)
        return setting.value
    except ServerSetting.DoesNotExist:
        pass
    try:
        return DEFAULTS[name]
    except KeyError:
        raise KeyError(f"No setting in DB and no default value for key {name}")


def get_setting_boolean(name):
    """ Return True or False for a given configuration setting or default value. """
    return bool(get_setting_string(name))



