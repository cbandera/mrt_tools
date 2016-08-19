from mrt_tools import CredentialManager as cm
from mrt_tools.settings import user_settings
import subprocess
import click
import os


def get_gituserinfo(quiet=False):
    """Read in git user infos."""

    # Check whether git is installed
    (__, dpkg_err) = subprocess.Popen("dpkg -s git", shell=True, stdout=subprocess.PIPE).communicate()

    # Read out username and email
    (name, name_err) = subprocess.Popen("git config --get user.name", shell=True,
                                        stdout=subprocess.PIPE).communicate()
    (email, mail_err) = subprocess.Popen("git config --get user.email", shell=True,
                                         stdout=subprocess.PIPE).communicate()
    (credential_helper, credential_err) = subprocess.Popen("git config --get credential.helper", shell=True,
                                                           stdout=subprocess.PIPE).communicate()

    # Check whether git is configured
    if not quiet:
        if dpkg_err is not None:
            click.echo("Git not found, installing...")
            subprocess.call("sudo apt-get install git", shell=True)
        if name_err is not None or name == "":
            name = click.prompt("Git user name not configured. Please enter your first and last name")
            set_gituserinfo(name=name)
        if mail_err is not None or email == "":
            email = click.prompt("Git user email not configured. Please enter email")
            set_gituserinfo(email=email)
        if user_settings['Gitlab']['CACHE_GIT_CREDENTIALS_FOR_HTTPS_REPOS'] \
                and credential_helper != "cache --timeout={}".format(user_settings['Gitlab']['GIT_CACHE_TIMEOUT']):
            set_gituserinfo(credential_helper="cache --timeout={}".format(user_settings['Gitlab']['GIT_CACHE_TIMEOUT']))

    return {'name': name[:-1], 'email': email[:-1]}


def set_gituserinfo(name=None, email=None, credential_helper=None):
    if name is not None:
        subprocess.call("git config --global user.name '{}'".format(name), shell=True)
    if email is not None:
        subprocess.call("git config --global user.email '{}'".format(email), shell=True)
    if credential_helper is not None:
        subprocess.call("git config --global credential.helper '{}'".format(credential_helper), shell=True)


def test_git_credentials():
    # Test whether git credentials are still stored:
    if user_settings['Gitlab']['CACHE_GIT_CREDENTIALS_FOR_HTTPS_REPOS'] \
            and not os.path.exists(os.path.expanduser("~/.git-credential-cache/socket")):
        username, password = cm.credentialManager.get_credentials()
        cm.set_git_credentials(username, password)
