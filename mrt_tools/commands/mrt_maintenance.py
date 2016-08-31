from mrt_tools.CredentialManager import credentialManager, set_git_credentials
from mrt_tools.Git import set_gituserinfo
from mrt_tools.Package import check_and_update_cmakelists
from wstool import config as wstool_config
from mrt_tools.Workspace import Workspace
from mrt_tools.utilities import *
from mrt_tools.Gitlab import Gitlab
import getpass


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
            echo("{0}: {1}".format(index, item[:-1]))
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
                wprint("WARNING in {0}: URL declared in src/{1}/package.xml, differs from the git repo url for {"
                       "0}!".format(pkg_name.upper(), pkg_name))
                echo("PackageXML: {0}".format(xml_url))
                echo("Git repo  : {0}".format(git_url))
                if click.confirm("Replace the url in package.xml with the correct one?"):
                    subprocess.call("sed -i -e '/  <url/d' {0}".format(filename), shell=True)
                    insert_url(filename, git_url)
        if xml_url is not None and git_url is None:
            wprint(
                "WARNING in {0}: URL declared in package.xml, but {1} does not seem to be a remote repository!".format(
                    pkg_name.upper(), pkg_name))
            if click.confirm("Remove the url in package.xml?"):
                sprint("Fixing...")
                subprocess.call("sed -i -e '/  <url/d' {0}".format(filename), shell=True)
        if xml_url is None and git_url is not None:
            wprint("WARNING in {0}: No URL (or multiple) defined in package.xml!".format(pkg_name.upper()))
            if click.confirm("Insert (Replace) the url in package.xml with the correct one?"):
                subprocess.call("sed -i -e '/  <url/d' {0}".format(filename), shell=True)
                insert_url(filename, git_url)
        if xml_url is None and git_url is None:
            echo("INFO in {0}: Does not seem to be a git repository. You should use Version Control for your "
                        "code!".format(pkg_name.upper()))

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
@click.option("--this", is_flag=True, help="Use the package containing the current directory.")
def update_cmakelists(package, this):
    """Update CMAKELISTS"""
    ws = Workspace()
    catkin_packages = ws.get_catkin_package_names()

    # Read in newest CMakeLists.txt
    current_version = None

    # download newest version:
    echo("Downloading newest template from gitlab")
    git = Gitlab()
    mrt_build_repo = git.find_repo("mrt_build")
    new_cmakelists = git.server.getrawfile(mrt_build_repo['id'], "master", 'mrt_tools/templates/CMakeLists.txt')
    for line in new_cmakelists.splitlines():
        if line.startswith("#pkg_version="):
            current_version = line
            break
    if not current_version:
        eprint("current pkg_version could not be found.")

    if this:
        package = os.path.basename(ws.org_dir)
        if package not in catkin_packages:
            eprint("{0} does not seem to be a catkin package.".format(package))
    if not package:
        for pkg_name in catkin_packages:
            ws.cd_src()
            check_and_update_cmakelists(pkg_name, current_version)
    else:
        ws.cd_src()
        check_and_update_cmakelists(package, current_version)


@main.command(short_help="Rename project",
              help="This command renames a project. The CMakeLists.txt, package.xml and includes are adjusted "
                   "accordingly within this project. "
                   "Additionally, all other files in the repo get regexed.")
@click.argument("new_name", required=True)
def rename_pkg(new_name):
    """ """
    ws = Workspace()

    package = os.path.basename(ws.org_dir)
    catkin_packages = ws.get_catkin_package_names()
    if package not in catkin_packages:
        eprint("{0} does not seem to be a catkin package.".format(package))
    if new_name in catkin_packages:
        eprint("{0} does already exist in your workspace.".format(new_name))

    # Test files
    for dirName, subdirList, fileList in os.walk(ws.src + "/" + package):
        if "/.git" in dirName:
            continue
        for fname in fileList:
            if fname.endswith(".h") or fname.endswith(".hh") or fname.endswith(".hpp") \
                    or fname.endswith(".cc") or fname.endswith(".cpp"):
                # Adjust includes
                subprocess.call("sed -i -e 's:#include\s[\"<]" + package + "/:#include \"" + new_name + "/:g' " +
                                dirName + "/" + fname, shell=True)
            else:
                # Rename all other occurrences
                subprocess.call("sed -i -e 's/" + package + "/" + new_name + "/g' " + dirName + "/" + fname, shell=True)

    # Move include folder
    if os.path.exists(ws.src + "/" + package + "/include/" + package):
        shutil.move(ws.src + "/" + package + "/include/" + package, ws.src + "/" + package + "/include/" + new_name)

    # Test for git repo
    if not os.path.exists(ws.src + "/" + package + "/.git"):
        echo("Renamed package " + package + " to " + new_name)
        return

    os.chdir(ws.src + "/" + package)
    echo("The following files in this package have been changed:")
    subprocess.call("git status -s", shell=True)
    echo("")
    echo("Next steps:")
    echo("\t-Review changes")
    echo("\t-Commit changes")

    echo("")
    while ws.test_for_changes(package, quiet=True):
        click.prompt("Continue, when changes are commited and pushed...")

    echo("")
    click.confirm("Do you want to move the gitlab project now?", abort=True)
    echo("Moving gitlab project...")
    git = Gitlab()
    project = git.find_repo(package)
    namespace = project["namespace"]["name"]
    project_id = project["id"]
    if not git.server.editproject(project_id, name=new_name, path=new_name):
        eprint("There was a problem, moving the project. Aborting!")

    echo("Updating git remote...")
    os.chdir(ws.src + "/" + package)
    project = git.find_repo(new_name, namespace)
    new_url = project[git.get_url_string()]
    subprocess.call("git remote set-url origin " + new_url + " >/dev/null 2>&1", shell=True)

    echo("Updating local ws...")
    ws.cd_src()
    shutil.move(package, new_name)
    os.chdir(new_name)
    os.remove(ws.src + "/.rosinstall")
    ws.recreate_index(write=True)

    echo("")
    echo("Next steps:")
    echo("\t-Adjust includes in other packages")


@main.command(short_help="Reinitialise the workspace index",
              help="This command recreates the '.rosinstall' file, which is used by catkin and wstool. This might be "
                   "necessary, when you altered it, or removed packages by hand but did not delete their config entry.")
def update_rosinstall():
    """Reinitialise the workspace index"""
    ws = Workspace()
    ws.cd_src()
    wprint("Removing wstool database src/.rosinstall")
    os.remove(".rosinstall")
    echo("Initializing wstool...")
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
        git = Gitlab(quiet=quiet)
        repo_dicts = git.get_repos()
        if not repo_dicts:
            raise Exception
        if not quiet:
            echo("Update was successful")
    except:
        # In case the connection didn't succeed, the file is going to be flushed -> we don't seem to have a
        # connection anyway and don't want old data.
        if not quiet:
            echo("There was an error during update.")
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
              help="This command starts an editor to let you edit the configuration file. You can specify whether to "
                   "use https or ssh, whether to save your private API token locally, and for how long to cache your git "
                   "credentials.")
def settings():
    """
    Change the default configuration of mrt tools.
    """
    from mrt_tools.settings import CONFIG_FILE

    # Choose an appropriate editor
    try:
        # Test for x server
        x_server_runing = os.environ['DISPLAY']
        if x_server_runing is None:
            raise KeyError
        # If we use a GUI, try the default application or gedit
        options = ["gedit", "xdg-open"]
    except KeyError:
        # if it is a shell, try the environment variable EDITOR to specify the default editor.
        # Otherwise fallback to nano, or others.
        options = ["xdg-open", "vi", "vim", "nano"]
        try:
            options.append(os.environ['EDITOR'])
        except KeyError:
            pass

    open_exec = None
    while open_exec is None and len(options) != 0:
        editor = options.pop()
        open_exec = which(editor)

    subprocess.call("{} {}".format(editor, CONFIG_FILE), shell=True)


@main.command(short_help="Update you local copy of all package dependencies.",
              help="This will download every package.xml file from Gitlab, that you have access to. These files will "
                   "be used for reverse dependency lookup.")
def update_cached_deps():
    git = Gitlab()

    if os.path.exists(user_settings['Cache']['CACHED_DEPS_WS']):
        echo("Removing existing files in workspace")
        shutil.rmtree(user_settings['Cache']['CACHED_DEPS_WS'])
    os.makedirs(user_settings['Cache']['CACHED_DEPS_WS'])

    echo("Retrieving repo list")
    repo_list = list(git.server.getall(git.server.getprojects, per_page=100))

    echo("Downloading package.xml files")
    skipped_repos = []
    with click.progressbar(repo_list) as repos:
        branches = []
        for repo in repos:
            errcount = 0
            branches = git.server.getbranches(repo['id'])
            while not branches and errcount < 5:
                branches = git.server.getbranches(repo['id'])
                errcount += 1
            if errcount == 5:
                skipped_repos.append(repo['name'])
                continue

            for branch in branches:

                # TODO Test checksum before downloading?

                file_contents = git.server.getrawfile(repo['id'], branch['name'], 'package.xml')
                if file_contents is None or file_contents is False:
                    skipped_repos.append(repo['name'])
                    continue

                file_name = os.path.join(user_settings['Cache']['CACHED_DEPS_WS'], repo['namespace']['name'],
                                         repo['name'], branch['name'], 'package.xml')
                if not os.path.exists(os.path.dirname(file_name)):
                    os.makedirs(os.path.dirname(file_name))

                with open(file_name, 'w') as f:
                    f.write(file_contents)

    skipped_repos = set(skipped_repos)
    echo("Skipped the following repos:")
    for repo in skipped_repos:
        echo("- {}".format(repo))


@main.group()
def credentials():
    pass


def delete_credentials():
    # Remove saved credentials
    credentialManager.delete('username')
    credentialManager.delete('password')
    credentialManager.delete('token')

    # Remove cache
    if os.path.exists(os.path.expanduser("~/.git-credential-cache/socket")):
        os.remove(os.path.expanduser("~/.git-credential-cache/socket"))

    # Remove git info
    subprocess.call("git config --global --remove-section user", shell=True)

    # Remove SSH Key
    sshkeys = Gitlab.get_local_ssh_keys()
    if sshkeys:
        wprint("You have an ssh key stored on this machine. If you want to remove ALL of your userdata, "
               "please delete it manually.")
        for nr, key in enumerate(sshkeys):
            echo("\t" + str(nr + 1) + ")\t" + key.path)


@credentials.command(short_help="Remove all stored credentials from this machine.")
def remove():
    delete_credentials()


@credentials.command(short_help="Delete old and store new credentials.")
def reset():
    click.confirm("Deleting userdata first. Continue?", abort=True)
    delete_credentials()

    username = getpass.getuser()
    name = click.prompt("Please enter your first and last name")
    email = click.prompt("Please enter your email address")
    username = click.prompt("Please enter your Gitlab username", default=username)
    password = click.prompt("Please enter your Gitlab password", hide_input=True)
    set_gituserinfo(name=name, email=email)
    credentialManager.store('username', username)
    credentialManager.store('password', password)
    Gitlab()


@credentials.command(short_help="Provide credentials to be stored.")
@click.argument("username", required=True)
@click.argument("password", required=True)
def save(username, password):
    credentialManager.store('username', username)
    credentialManager.store('password', password)


@credentials.command(short_help="Show all stored credentials on this machine.")
def show():
    username = credentialManager.get_username(quiet=True)
    password = credentialManager.get_password(username, quiet=True) and "******"
    echo("")
    echo("Gitlab credentials")
    echo("==================")
    echo("(Current setting: '{}')".format(user_settings['Gitlab']['STORE_CREDENTIALS_IN']))
    echo("Username: {}".format(username))
    echo("Password: {}".format(password))
    echo("Token   : {}".format(credentialManager.get_token()))
    echo("")

    # Read out username and email
    (name, name_err) = subprocess.Popen("git config --get user.name", shell=True,
                                        stdout=subprocess.PIPE).communicate()
    (email, mail_err) = subprocess.Popen("git config --get user.email", shell=True,
                                         stdout=subprocess.PIPE).communicate()

    if name:
        name = name[:-1]
    if email:
        email = email[:-1]
    echo("Git credentials")
    echo("==================")
    echo("user.name    : {}".format(name))
    echo("user.email   : {}".format(email))
    if os.path.exists(os.path.expanduser("~/.git-credential-cache/socket")):
        echo("cached creds.: {}".format("Yes"))
    else:
        echo("cached creds.: {}".format("No"))
    echo("")


@credentials.command(short_help="Show all stored credentials on this machine.")
def update_cache():
    username, password = credentialManager.get_credentials()
    set_git_credentials(username, password)
