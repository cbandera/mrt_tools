from mrt_tools.settings import user_settings
from builtins import str
import subprocess
import urllib2
import zipfile
import shutil
import fnmatch
import click
import sys
import os
import re
import xml.etree.ElementTree as ET


def eprint(message):
    """
    Prints a red error message  to consoleend exits with error.
    :param message:
    :return: None
    """
    click.secho(message, fg="red")
    sys.exit(1)


def wprint(message):
    """
    Prints a yellow warning message to console
    :param message:
    :return: None
    """
    click.secho(message, fg="yellow")


def sprint(message):
    """
    Prints a green success message to console
    :param message:
    :return: None
    """
    click.secho(message, fg="green")


def echo(message):
    """
    Prints a message to console
    :param message:
    :return: None
    """
    echo(message)


def convert_to_snake_case(name):
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    s1 = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
    s1 = re.sub('__', '_', s1)
    return s1


def convert_to_camel_case(name):
    s1 = convert_to_snake_case(name)
    return "".join(x.capitalize() if x else '_' for x in s1.split("_"))


def is_ros_sourced():
    # Test whether ros is sourced
    return "ROS_ROOT" in os.environ


def get_script_root():
    """
    Get the path to the install location of this script.
    :return: path
    """
    return os.path.dirname(os.path.realpath(__file__))


def find_by_pattern(pattern, path):
    """
    Searches for a file within a directory
    :param pattern: Name to search for
    :param path: Search path
    :return: List of paths
    """
    result = []
    for root, dirs, files in os.walk(path):
        for name in files:
            if fnmatch.fnmatch(name, pattern):
                result.append(os.path.join(root, name))
    return result


def get_user_choice(items, extra=None, prompt="Please choose a number", default=None):
    """
    Function to make user choose from a list of options
    :param items: List of strings
    :param extra: String or list of strings with additional options
    :param prompt: Prompt string
    :param default: Default choice
    :return: Index of choice, choice string
    """
    # Test for extra choices
    if not extra:
        extra = []
    if not isinstance(extra, list):
        extra = [extra]

    # Create choices
    choices = {index: item for index, item in enumerate(items + extra)}

    # Print choices
    for key, value in choices.items():
        echo("(" + str(key) + ") " + str(value))

    # Get choice
    while True:
        user_choice = click.prompt(prompt + ' [0-' + str(choices.keys()[-1]) + ']', type=int, default=default)
        if user_choice in choices.keys():
            return user_choice, choices[user_choice]


def touch(filename, times=None):
    """create a file"""
    if os.path.exists(filename):
        with open(filename, 'a'):
            os.utime(filename, times)
    else:
        if not os.path.exists(os.path.dirname(filename)):
            os.makedirs(os.path.dirname(filename))
        with open(filename, 'w'):
            os.utime(filename, times)


def update_apt_and_ros_packages():
    f_null = open(os.devnull, 'w')
    subprocess.call(["sudo", "apt-get", "update"], stdout=f_null, stderr=f_null)
    subprocess.check_call(["rosdep", "update"], stdout=f_null)


def zip_files(files, archive):
    """Add file to a zip archive"""
    zf = zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED)
    for filename in files:
        if isinstance(filename, tuple):
            zf.write(filename[0], arcname=filename[1])
        else:
            zf.write(filename)
    zf.close()


def get_rosdeps():
    """ Returns a list of all rosdep dependencies known"""
    process = subprocess.Popen(['rosdep', 'db'], stdout=subprocess.PIPE)
    output, __ = process.communicate()
    return [line.split(" -> ")[0] for line in output.split("\n") if " -> " in line]


def set_eclipse_project_setting(ws_root):
    build_dir = os.path.join(ws_root, "build")
    for project in find_by_pattern(".project", build_dir):
        os.chdir(os.path.dirname(project))
        # set environment variables
        subprocess.call(
            'awk -f $(rospack find mk)/eclipse.awk .project > .project_with_env && mv .project_with_env .project',
            shell=True)

        # add support for indexing
        if not os.path.isfile("./.settings/language.settings.xml"):
            if not os.path.isdir("./.settings"):
                os.mkdir("./.settings")
        script_dir = get_script_root()
        shutil.copy(script_dir + "/templates/language.settings.xml", "./.settings")

        # hide catkin files, etc.
        if os.path.isfile("./.project"):
            template_tree = ET.parse(script_dir + "/templates/project_filter.xml")
            template_root = template_tree.getroot()

            project_tree = ET.parse("./.project")
            project_root = project_tree.getroot()

            project_root.append(template_root)
            project_tree.write("./.project", encoding="UTF-8", xml_declaration=True)


def cache_repos():
    # For caching
    import time

    now = time.time()
    try:
        # Read in last modification time
        last_mod_lock = os.path.getmtime(user_settings['Cache']['CACHE_LOCK_FILE'])
    except OSError:
        # Set modification time to 2 * default_repo_cache_time ago
        last_mod_lock = now - 2 * user_settings['Cache']['CACHE_LOCK_DECAY_TIME']
        touch(user_settings['Cache']['CACHE_LOCK_FILE'])

    # Keep caching process from spawning several times
    if (now - last_mod_lock) > user_settings['Cache']['CACHE_LOCK_DECAY_TIME']:
        touch(user_settings['Cache']['CACHE_LOCK_FILE'])
        devnull = open(os.devnull, 'wb')  # use this in python < 3.3; python >= 3.3 has subprocess.DEVNULL
        subprocess.Popen(['mrt maintenance update_repo_cache --quiet'], shell=True, stdin=devnull, stdout=devnull,
                         stderr=devnull)


def import_repo_names(ctx=None, incomplete=None, cwords=None, cword=None):
    """
    Try to read in repos from cached file.
    If file is older than default_repo_cache_time seconds, a new list is retrieved from server.
    """
    try:
        # Read in repo list from cache
        with open(user_settings['Cache']['CACHE_FILE'], "r") as f:
            repos = f.read()
        return repos.split(",")[:-1]
    except OSError:
        return []


# TODO maybe create a file called AutoDeps or DependencyManagement...
def changed_base_yaml():
    echo("Testing for changes in rosdeps...")
    import hashlib
    hasher = hashlib.md5()

    # Read hashes
    try:
        base_yaml = urllib2.urlopen(user_settings['Dependencies']['BASE_YAML_URL']).read()
        hasher.update(base_yaml)
        new_hash = hasher.hexdigest()
    except IOError:
        wprint("Could not read base yaml file at {}. Not testing for changed rosdep db".format(
            user_settings['Dependencies']['BASE_YAML_URL']))
        return False

    try:
        with open(user_settings['Dependencies']['BASE_YAML_HASH_FILE'], 'r') as f:
            old_hash = f.read()
    except IOError:
        old_hash = ""
        if not os.path.exists(os.path.dirname(user_settings['Dependencies']['BASE_YAML_HASH_FILE'])):
            os.makedirs(os.path.dirname(user_settings['Dependencies']['BASE_YAML_HASH_FILE']))
        with open(user_settings['Dependencies']['BASE_YAML_HASH_FILE'], 'wb') as f:
            f.write("")

    # Compare hashes
    if old_hash == new_hash:
        return False
    else:
        with open(user_settings['Dependencies']['BASE_YAML_HASH_FILE'], 'w') as f:
            f.truncate()
            f.write(new_hash)
        return True


def get_help_text(command):
    """
    Adds '\b' before every paragraph to keep correct formatting
    :return: Formatted help text
    """
    command_args = command.split()
    try:
        help_text = subprocess.check_output(command_args)
    except OSError:
        help_text = "*** ERROR in get_help_text() ... please contact the package maintainer. ***"

    # reformatted = "This is the help text for '{}':\n\n\b\n".format(command)
    reformatted = "\b\n"
    for line in help_text.splitlines(True):
        if line == "\n":
            line = "\b\n"
        reformatted += line
    return reformatted


def which(program):
    """Custom version of the ``which`` built-in shell command. Taken from catkin_tools!

    Searches the pathes in the ``PATH`` environment variable for a given
    executable name. It returns the full path to the first instance of the
    executable found or None if it was not found.

    :param program: name of the executable to find
    :type program: str
    :returns: Full path to the first instance of the executable, or None
    :rtype: str or None
    """

    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    fpath, _ = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ.get('PATH', os.defpath).split(os.pathsep):
            path = path.strip('"')
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file
    return None


self_dir = get_script_root()
cache_repos()
