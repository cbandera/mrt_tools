#!/bin/python
from mrt_py_tools import mrt_base_tools
import os
import distutils.util
import subprocess
import click
import sys


@click.command()
def main():
    """ This script initializes a catkin workspace in the current folder. """
    init_repo = True

    workspace_folder = mrt_base_tools.get_workspace_root_folder(os.getcwd())
    print workspace_folder
    if not (workspace_folder == "/" or  workspace_folder == ""):
        click.secho("Catkin workspace exists already.", fg="red")
        sys.exit(1)

    # Test whether directory is empty
    if os.listdir("."):
        choice_str = raw_input("The repository folder is not empty. Would you like to continue? [y/N] ")
        if choice_str == "":
            choice_str = "n"
        init_repo = distutils.util.strtobool(choice_str)

    if init_repo:
        os.mkdir("src")
        subprocess.call("catkin init", shell=True)
        os.chdir("src")
        subprocess.call("wstool init", shell=True)
        subprocess.call("catkin build", shell=True)