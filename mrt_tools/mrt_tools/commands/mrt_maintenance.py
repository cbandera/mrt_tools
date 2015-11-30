from wstool import config as wstool_config
from mrt_tools.settings import user_settings
from mrt_tools.CredentialManager import *
from mrt_tools.Workspace import Workspace
from mrt_tools.utilities import *
from mrt_tools.Git import Git


########################################################################################################################
# Fixes
########################################################################################################################
@click.group()
def main():
    """Repair tools..."""


@main.command(short_help="Updates missing or wrong URL into package.xml",
              help="This command will test, whether your git URL is the same as the URL specified in "
                   "package.xml. If not, it will ask you whether to change it and asks you to specify a line number. "
                   "NOTE: Up to now, normally the ssh URL is specified in the package.xml. If you are working with "
                   "https you might get asked to change the URL in every package!")
def update_url_in_package_xml():
    """Updates missing or wrong URL into package.xml"""

    def insert_url(file_name, url):
        with open(file_name, 'r') as f:
            contents = f.readlines()
        click.clear()
        for index, item in enumerate(contents):
            click.echo("{0}: {1}".format(index, item[:-1]))
        linenumber = click.prompt("\n\nPlease specify the line to insert the url in", type=click.INT)
        contents.insert(linenumber, '  <url type="repository">{0}</url>\n'.format(url))
        contents = "".join(contents)
        with open(file_name, 'w') as f:
            f.write(contents)
        click.clear()
        if click.confirm("OK, did that. Commit these changes?"):
            org_dir = os.getcwd()
            os.chdir(os.path.dirname(file_name))
            subprocess.call("git add {0}".format(file_name), shell=True)
            subprocess.call("git commit -m 'Added repository url to package.xml'", shell=True)
            os.chdir(org_dir)

    ws = Workspace()
    ws.catkin_pkg_names = ws.get_catkin_package_names()
    ws.config = wstool_config.Config([], ws.src)
    ws.cd_src()

    for pkg_name in ws.catkin_pkg_names:
        filename = os.path.join(ws.src, pkg_name, "package.xml")
        # Try reading it from git repo
        try:
            # TODO Maybe try to always get the https/ssh url? Right now, it is only checked against how YOU have it
            # configured.
            with open(pkg_name + "/.git/config", 'r') as f:
                git_url = next(line[7:-1] for line in f if line.startswith("\turl"))
        except (IOError, StopIteration):
            git_url = None

        # Try to read it from package xml
        try:
            if len(ws.catkin_pkgs[pkg_name].urls) > 1:
                raise IndexError
            xml_url = ws.catkin_pkgs[pkg_name].urls[0].url
        except IndexError:
            xml_url = None

        # Testing all cases:
        if xml_url is not None and git_url is not None:
            if xml_url != git_url:
                click.secho("WARNING in {0}: URL declared in src/{1}/package.xml, differs from the git repo url for {"
                            "0}!".format(pkg_name.upper(), pkg_name),
                            fg="red")
                click.echo("PackageXML: {0}".format(xml_url))
                click.echo("Git repo  : {0}".format(git_url))
                if click.confirm("Replace the url in package.xml with the correct one?"):
                    subprocess.call("sed -i -e '/  <url/d' {0}".format(filename), shell=True)
                    insert_url(filename, git_url)
        if xml_url is not None and git_url is None:
            click.secho("WARNING in {0}: URL declared in package.xml, but {1} does not seem to be a remote "
                        "repository!".format(pkg_name.upper(), pkg_name), fg="yellow")
            if click.confirm("Remove the url in package.xml?"):
                click.secho("Fixing...", fg="green")
                subprocess.call("sed -i -e '/  <url/d' {0}".format(filename), shell=True)
        if xml_url is None and git_url is not None:
            click.secho("WARNING in {0}: No URL (or multiple) defined in package.xml!".format(pkg_name.upper()),
                        fg="yellow")
            if click.confirm("Insert (Replace) the url in package.xml with the correct one?"):
                subprocess.call("sed -i -e '/  <url/d' {0}".format(filename), shell=True)
                insert_url(filename, git_url)
        if xml_url is None and git_url is None:
            click.secho("INFO in {0}: Does not seem to be a git repository. You should use Version Control for your "
                        "code!".format(pkg_name.upper()), fg="cyan")

        if git_url is not None:
            ws.add(pkg_name, git_url, update=False)

    ws.write()


@main.command(short_help="Update CMakeLists.txt",
              help="This command will compare the Version tag of a projects CMakeLists with the newest template. If "
                   "they differ, a new CMakeLists.txt is created from the template and the diff tool 'meld' is "
                   "launched, so you can see the differences. Please take special care, to port all functionality, "
                   "that might have been add to the old CMake file to the new file. NOTE: You need to have 'meld' "
                   "installed.")
@click.argument("package", required=False)
@click.option("--this", is_flag=True)
def update_cmakelists(package, this):
    """Update CMAKELISTS"""
    ws = Workspace()
    catkin_packages = ws.get_catkin_package_names()

    # Read in newest CMakeLists.txt
    current_version = None
    with open(self_dir + "/templates/CMakeLists.txt") as f:
        for line in f:
            if line.startswith("#pkg_version="):
                current_version = line[:-1]
                break
    if not current_version:
        click.secho("current pkg_version could not be found.", fg='red')
        sys.exit(1)

    if this:
        package = os.path.basename(ws.org_dir)
        if package not in catkin_packages:
            click.secho("{0} does not seem to be a catkin package.".format(package), fg="red")
            sys.exit(1)
    if not package:
        for pkg_name in catkin_packages:
            ws.cd_src()
            check_and_update_cmakelists(pkg_name, current_version)
    else:
        ws.cd_src()
        check_and_update_cmakelists(package, current_version)

    click.secho("The commit is not yet pushed, in case you didn't really test the changes yet... You "
                "didn't, right? Ok, so go ahead and test them and then run 'mrt wstool update'", fg="yellow")


@main.command(short_help="Reinitialise the workspace index",
              help="This command recreates the '.rosinstall' file, which is used by catkin and wstool. This might be "
                   "necessary, when you altered it, or removed packages by hand but did not delete their config entry.")
def update_rosinstall():
    """Reinitialise the workspace index"""
    ws = Workspace()
    ws.cd_src()
    click.secho("Removing wstool database src/.rosinstall", fg="yellow")
    os.remove(".rosinstall")
    click.echo("Initializing wstool...")
    ws.recreate_index(write=True)


@main.command(short_help="Updates the cached list of repos.",
              help="This command loads the current list of repos from the server and caches them in a file for bash "
                   "autocompletion. This command is run every time you use the mrt tools, so normally there is no "
                   "need to call this manually.")
@click.option("--quiet", is_flag=True)
def update_repo_cache(quiet):
    """
    Read repo list from server and write it into caching file.
    :rtype : object
    """
    # Because we are calling this during autocompletion, we don't wont any errors.
    # -> Just exit when something is not ok.
    error_occurred = False
    try:
        # Connect
        git = Git(quiet=quiet)
        repo_dicts = git.get_repos()
        if not repo_dicts:
            raise Exception
        if not quiet:
            click.echo("Update was successful")
    except:
        # In case the connection didn't succeed, the file is going to be flushed -> we don't seem to have a
        # connection anyway and don't want old data.
        if not quiet:
            click.echo("There was an error during update.")
        error_occurred = True
        repo_dicts = []
        # Remove lock file, so that it will soon be tried again.
        try:
            os.remove(user_settings['Cache']['CACHE_LOCK_FILE'])
        except OSError:
            pass

    dir_name = os.path.dirname(user_settings['Cache']['CACHE_FILE'])
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)
    with open(user_settings['Cache']['CACHE_FILE'], "w") as f:
        if error_occurred:
            f.write("AN_ERROR_OCCURRED, CACHING_WAS_UNSUCCESSFUL,")
        else:
            for r in repo_dicts:
                f.write(r["name"] + ",")


@main.command(short_help="Change the default configuration of mrt tools.",
              help="This command starts gedit to let you edit the configuration file. You can specify whether to use "
                   "https or ssh, whether to save your private API token locally, and for how long to cache your git "
                   "credentials.")
def settings():
    """
    Change the default configuration of mrt tools.
    """
    from mrt_tools.settings import CONFIG_FILE
    subprocess.call("gedit {}".format(CONFIG_FILE), shell=True)


@main.group()
def credentials():
    pass


@credentials.command(short_help="Remove all stored credentials from this machine.")
def delete():
    try:
        delete_credential('username')
    except:
        pass
    try:
        delete_credential('password')
    except:
        pass
    try:
        delete_credential('token')
    except:
        pass


@credentials.command(short_help="Show all stored credentials on this machine.")
def show():
    username = get_username(quiet=True)
    password = get_password(username, quiet=True) and "******"
    click.echo("Gitlab credentials")
    click.echo("==================")
    click.echo("Username: {}".format(username))
    click.echo("Password: {}".format(password))
    click.echo("Token   : {}".format(get_token()))
