from distutils.sysconfig import get_python_lib
from mrt_tools.settings import user_settings
from mrt_tools.utilities import eprint
import mrt_tools.commands
import os
import click
import sys


"""
This is the landing point for the cli tool.

sudo: We experienced difficulties, when the mrt tools were used with superuser priviliges, as cache and settings
files were not readable anymore for the normal user. Therefor we do not allow root usage.

Virtualenv: If the tools are installed a virtualenv, we activate it before starting any command, so that all
subprocesses called are executed from inside the virtualenv.

All subcommands lie in the 'commands' folder and need to start with 'mrt_'. They will be automatically parsed and
added as subcommands.
"""

# TODO GENERAL
# TODO test whether we still need a virtualenv
# TODO Think about documentation -> sphinx? readthedocs?

# Test for sudo
if os.getuid() == 0:
    if not user_settings['Other']['ALLOW_ROOT']:
        eprint("Should not be run as root. Please use without sudo.")

# Activate virtualenv if found
venv_activate_file = None
current_dir = get_python_lib()
while current_dir != "/" and current_dir != "":
    file_path = os.path.join(current_dir, "bin", "activate_this.py")
    if os.path.isfile(file_path):
        venv_activate_file = file_path
        break
    current_dir = os.path.dirname(current_dir)
if venv_activate_file:
    execfile(venv_activate_file, dict(__file__=venv_activate_file))

# Load commands
plugin_folder = os.path.dirname(mrt_tools.commands.__file__)


class MyCLI(click.MultiCommand):
    def list_commands(self, ctx):
        rv = []
        for filename in os.listdir(plugin_folder):
            if filename.startswith('mrt_') and filename.endswith('.py'):
                rv.append(filename[4:-3])
        rv.sort()
        return rv

    def get_command(self, ctx, name):
        ns = {}
        fn = os.path.join(plugin_folder, 'mrt_' + name + '.py')
        try:
            with open(fn) as f:
                code = compile(f.read(), fn, 'exec')
                eval(code, ns, ns)
        except IOError:
            eprint("No such subcommand: '{0}'".format(name))
        return ns['main']


cli = MyCLI(help='The swiss army knife for ROS developers.')

if __name__ == '__main__':
    cli()
