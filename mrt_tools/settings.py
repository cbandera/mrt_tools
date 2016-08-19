#!/usr/bin/python
import ConfigParser
import click
import os

"""
Settings

Here, all configurable options for the tools are listed. They are stored in yaml format in a persistent file in the
users home folder and will be read every time, before starting up the mrt tools.
Default settings are listed here, but will be overridden by user settings.
The read and write functions will make sure to silently update settings to the newest version,
dropping keys that are no longer used and adding those, that are missing.
"""

CONFIG_DIR = os.path.expanduser("~/.mrt_tools")
CONFIG_FILE = os.path.join(CONFIG_DIR, "mrt_tools.cfg")

# Default settings
default_settings = {
    'Cache': {
        'CACHE_FILE': os.path.join(CONFIG_DIR, "gitlab_packages"),
        'CACHE_LOCK_FILE': os.path.join(CONFIG_DIR, ".package_cache_lock"),
        'CACHE_LOCK_DECAY_TIME': 30,  # in seconds
        'CACHED_DEPS_WS': os.path.join(CONFIG_DIR, "deps_cache_ws"),
    },
    'Gitlab': {
        'HOST_URL': "https://gitlab.mrt.uni-karlsruhe.de",
        'CACHE_GIT_CREDENTIALS_FOR_HTTPS_REPOS': True,
        'GIT_CACHE_TIMEOUT': 900,  # in seconds
        'STORE_CREDENTIALS_IN': "",
        'STORE_USERNAME': True,
        'STORE_PASSWORD': True,
        'STORE_API_TOKEN': True,
        'USE_SSH': False,
    },
    'Snapshot': {
        'FILE_ENDING': ".snapshot",
        'SNAPSHOT_VERSION': "0.1.0",
        'VERSION_FILE': "snapshot.version"
    },
    'Catkin': {
        'SHOW_WARNINGS_DURING_COMPILATION': True,
        'DEFAULT_BUILD_TYPE': "RelWithDebInfo",
    },
    'Dependencies':{
        'BASE_YAML_URL': "https://raw.githubusercontent.com/KIT-MRT/mrt_cmake_modules/master/yaml/base.yaml",
        'BASE_YAML_HASH_FILE': os.path.join(CONFIG_DIR, "base_yaml_hash"),
    },
    'ROS': {
        'NamingRegexPattern': "\b[a-zA-Z][a-zA-Z_0-9]+",
    },
    'Other': {
        'ALLOW_ROOT': False,
    }
}


def read_settings(settings, config_file=CONFIG_FILE):
    # Read in config file
    config = ConfigParser.SafeConfigParser()
    config.read(config_file)

    # Test for sections
    for section, section_dict in settings.iteritems():
        # Test for section
        if not config.has_section(section):
            # Default values will be taken
            continue
        # Go through keys
        for key, value in section_dict.iteritems():
            if config.has_option(section, key):
                # Update our default settings dict with loaded data
                if isinstance(value, bool):
                    settings[section][key] = config.getboolean(section, key)
                elif isinstance(value, int):
                    settings[section][key] = config.getint(section, key)
                else:
                    settings[section][key] = config.get(section, key)
            else:
                # Default values will be taken
                continue
    return settings


def write_settings(settings, config_file=CONFIG_FILE):
    # Create new config
    config = ConfigParser.SafeConfigParser()

    # Test for sections
    for section, section_dict in settings.iteritems():
        config.add_section(section)

        # Go through keys
        for key, value in section_dict.iteritems():
            config.set(section, key, str(value))

    # Writing our configuration file
    if not os.path.exists(os.path.dirname(config_file)):
        os.makedirs(os.path.dirname(config_file))
    with open(config_file, 'wb') as f:
        config.write(f)

# Test for first time usage
if not os.path.isfile(CONFIG_FILE):
    click.echo("Looks like this is the first time you use this tools. Have a look at the settings, by using 'mrt "
               "maintenance settings' in order to configure these tools")

# Read user settings
user_settings = read_settings(default_settings, CONFIG_FILE)
write_settings(user_settings, CONFIG_FILE)
