from mrt_tools.settings import user_settings, write_settings
from mrt_tools.utilities import get_user_choice, eprint, wprint, sprint, echo
from collections import OrderedDict
import subprocess
import getpass
import click
import sys

"""
CredentialManager

The CredentialManager is a class to store you gitlab credentials for you, so you don't have to retype them every time they are needed.
There are several backends which you can choose from. Right now the following are supported:
- The BaseCredentialManager will store them just for a single session.
- The DummyCredentialManager will not store them at all
- The KeyringCredentialManager will store the credential permanently and let's you choose between a file or the
GnomeKeyring as a backend.

Through the settings, you can choose which credentials to save:
- Username
- Password
- API Token
"""


def store_this(key):
    if key == "username" and not user_settings['Gitlab']['STORE_USERNAME']:
        return False
    if key == "password" and not user_settings['Gitlab']['STORE_PASSWORD']:
        return False
    if key == "token" and not user_settings['Gitlab']['STORE_API_TOKEN']:
        return False
    return True


class BaseCredentialManager(object):
    credentialStorage = {}

    def get_credentials(self, quiet=False):
        username = self.get_username(quiet)
        password = self.get_password(username, quiet)
        return username, password

    def get_username(self, quiet=False):
        username = self.get("username")

        if username is None and not quiet:
            username = getpass.getuser()
            username = click.prompt("Please enter Gitlab username", default=username)
            self.store("username", username)

        return username

    def get_password(self, username, quiet=False):
        password = self.get("password")

        if password is None and not quiet:
            password = click.prompt("Please enter Gitlab password for user {}".format(username), hide_input=True)
            self.store("password", password)

        return password

    def get_token(self):
        return self.get("token")

    def store(self, key, value):
        if not store_this(key):
            return
        self.credentialStorage[key] = value

    def get(self, key):
        try:
            return self.credentialStorage[key]
        except KeyError:
            return None

    def delete(self, key):
        try:
            del self.credentialStorage[key]
        except KeyError:
            pass


class DummyCredentialManager(BaseCredentialManager):
    def get_username(self, quiet=False):
        return None

    def get_password(self, username, quiet=False):
        return None

    def store(self, key, value):
        pass


class KeyringCredentialManager(BaseCredentialManager):
    """Base class for all keyring credential managers"""
    SERVICE_NAME = "mrt_tools"

    def get(self, key):
        return keyring.get_password(self.SERVICE_NAME, key)

    def store(self, key, value):
        sprint("Storing {} in keyring.".format(key))
        if not store_this(key):
            return
        keyring.set_password(self.SERVICE_NAME, key, value)

    def delete(self, key):
        try:
            keyring.delete_password(self.SERVICE_NAME, key)
            sprint("Removed {} from keyring".format(key))
        except keyring.errors.PasswordDeleteError:
            pass


class GnomeCredentialManager(KeyringCredentialManager):
    def __init__(self):
        keyring.set_keyring(keyring.backends.Gnome.Keyring())


class FileCredentialManager(KeyringCredentialManager):
    def __init__(self):
        keyring.set_keyring(keyring.backends.file.PlaintextKeyring())


# Using ordered dict, so that 'get_user_choice' is displayed correctly.
CredentialManagers = OrderedDict()
CredentialManagers['BaseCredentialManager'] = (BaseCredentialManager, "Does not save any credentials.")
CredentialManagers['DummyCredentialManager'] = (
    DummyCredentialManager, "DEBUG ONLY! This will not ask for a password at all.")

try:  # Test whether keyring is available
    import keyring

    for i in range(5):  # Sometimes, it just wont work right away, so we just try several times
        try:  # Test whether Gnome Keyring is available
            keyring.set_keyring(keyring.backends.Gnome.Keyring())
            CredentialManagers['GnomeCredentialManager'] = (GnomeCredentialManager, "Uses Ubuntu Default Gnome Keyring "
                                                                                    "protected with your user account")
            break
        except (AttributeError, keyring.errors.PasswordSetError, NameError):
            pass
    try:
        keyring.set_keyring(keyring.backends.file.PlaintextKeyring())
        CredentialManagers['FileCredentialManager'] = (FileCredentialManager, "Stores credentials in an encoded file "
                                                                              "within your account")
    except AttributeError:
        pass
except ImportError:
    pass

# Smooth transition to new version:
if user_settings['Gitlab']['STORE_CREDENTIALS_IN'] not in CredentialManagers.keys():
    if not sys.stdout.isatty():
        # You're NOT running in a real terminal, create DummyCredentialManager to avoid being prompted
        user_settings['Gitlab']['STORE_CREDENTIALS_IN'] = "DummyCredentialManager"
    else:
        echo("")
        wprint("Please choose one of the available backends for saving your credentials. \n"
                    "These settings can be changed with 'mrt maintenance settings')")
        echo("")
        user_choice, _ = get_user_choice(['{:25s}-> {}'.format(manager, description[1]) for manager,
                                                                                            description in
                                          CredentialManagers.items()], default=0,
                                         prompt="Where do you want to save your credentials?")
        echo("")
        user_settings['Gitlab']['STORE_CREDENTIALS_IN'] = CredentialManagers.keys()[user_choice]
        write_settings(user_settings)

# Choose the correct Credential Manager
credentialManager = CredentialManagers[user_settings['Gitlab']['STORE_CREDENTIALS_IN']][0]()


def set_git_credentials(username, password):
    url = user_settings['Gitlab']['HOST_URL']
    if url.startswith("https://"):
        host = url[8:]
    elif url.startswith("http://"):
        host = url[7:]
    else:
        host = url
    git_process = subprocess.Popen("git credential-cache store", shell=True, stdin=subprocess.PIPE)
    git_process.communicate(
        input="protocol=https\nhost={}\nusername={}\npassword={}".format(host, username, password))
