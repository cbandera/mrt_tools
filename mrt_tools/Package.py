from mrt_tools.utilities import self_dir, eprint, touch, echo, FullParser, ET
from mrt_tools.Git import get_gituserinfo
from string import Template
import subprocess
import shutil
import click
import os


# TODO Create custom package class as wrapper for all package relevant functions
class Package(object):
    def __init__(self, name):
        self.name = name

    def create_from_template(self):
        pass


class Manifest(object):
    def __init__(self, path):
        self.path = path
        if os.path.exists(self.path):
            self.manifest = ET.parse(path, parser=FullParser())

    def create_from_template(self, pkgname, username, useremail):
        self.manifest = ET.parse(os.path.join(self_dir, "templates/package.xml"), parser=FullParser())
        for e in self.manifest.findall("author"):
            e.text = username
            e.attrib['email']=useremail
        for e in self.manifest.findall("maintainer"):
            e.text = username
            e.attrib['email']=useremail
        for e in self.manifest.findall("name"):
            e.text = pkgname

        self.write()

    def write(self):
        self.manifest.write(self.path)

    def add_depend(self, name):
        tags = [c.tag for c in self.manifest.getroot()._children]
        try:
            index = tags.index("export")
        except ValueError:
            try:
                index = [i for i, x in enumerate(tags) if x == "depend"][-1] + 1
            except IndexError:
                index = -1
        existing_depends = [e.text for e in self.manifest.findall("depend")]
        if name not in existing_depends:
            element = ET._Element("depend")
            element.text = name
            element.tail = "\n  "
            self.manifest.getroot().insert(index, element)

    def add(self, tag, value, attributes=None, index=0):
        element = ET._Element(tag)
        element.text = value
        if attributes is not None:
            element.attrib = attributes
        element.tail = "\n  "
        self.manifest.getroot().insert(index, element)


# TODO use python templates?
def create_files(pkg_name, pkg_type, ros):
    # Readme and test file
    shutil.copyfile(self_dir + "/templates/README.md", "README.md")
    shutil.copyfile(self_dir + "/templates/test.cpp", "./test/test_" + pkg_name + ".cpp")
    # Package.xml
    user=get_gituserinfo()
    manifest = Manifest("package.xml")
    manifest.create_from_template(
        pkg_name, username=user['name'].decode("utf8"), useremail=user['email'].decode("utf8"))
    if ros:
        manifest.add("build_depend","rosparam_handler", index=8)
        manifest.add("build_depend","message_generation", index=9)
        manifest.add("exec_depend","message_runtime", index=10)
        manifest.add("build_depend","roscpp", index=12)
        manifest.add("depend","roslib", index=13)
        manifest.add("depend","nodelet", index=14)
    manifest.write()

    create_cmakelists(pkg_name, pkg_type, ros, self_dir)


# TODO really think about how to handle cmake templates
def create_cmakelists(pkg_name, pkg_type, ros, self_dir):
    # CMakeLists.txt
    # build mask @12|34@
    # pos1: non ros package
    # pos2: ros package
    # pos3: library
    # pos4: executable
    pattern = "@"
    if ros:
        pattern += ".x"
    else:
        pattern += "x."
    pattern += "|"

    if pkg_type == "lib":
        pattern += "x.@"
    elif pkg_type == "exec":
        pattern += ".x@"

    shutil.copyfile(self_dir + "/templates/CMakeLists.txt", "./CMakeLists.txt")
    subprocess.call("sed -i " +
                    "-e 's/^" + pattern + " //g' " +
                    "-e '/^@..|..@/d' " +
                    "-e 's/\${CMAKE_PACKAGE_NAME}/" + pkg_name + "/g' " +
                    "CMakeLists.txt", shell=True)


# TODO move this package related stuff into own file?
def create_directories(pkg_name, pkg_type, ros):
    # Check for already existing folder
    if os.path.exists("src/" + pkg_name):
        eprint("ERROR: The folder with the name ./src/" + pkg_name +
               " exists already. Please move it or choose a different package name.")

    # Create folders
    os.makedirs("src/" + pkg_name)
    os.chdir("src/" + pkg_name)

    if pkg_type == "lib":
        os.makedirs("include/" + pkg_name + "/internal")
        touch("include/" + pkg_name + "/internal/.gitignore")

    os.mkdir("test")
    os.mkdir("src")
    touch("src/.gitignore")

    if ros is True and pkg_type == "exec":
        os.mkdir("res")
        os.makedirs("launch/params")
        touch("launch/params/.gitignore")


# TODO remove this function
def check_and_update_cmakelists(pkg_name, current_version):
    os.chdir(pkg_name)
    with open("CMakeLists.txt") as f:
        pkg_version = f.readline()[:-1]
    if pkg_version != current_version:
        echo("\n{0}: Package versions not matching: {1}<->{2}".format(pkg_name.upper(), pkg_version,
                                                                      current_version))
        if click.confirm("Update CMakeLists?"):
            ros = click.confirm("ROS package?")
            pkg_type = ""
            while not ((pkg_type == "lib") or (pkg_type == "exec")):
                pkg_type = click.prompt("[lib/exec]")

            shutil.copyfile("CMakeLists.txt", "CMakeLists.txt.bak")
            create_cmakelists(pkg_name, pkg_type, ros, self_dir)

            process = subprocess.Popen("meld CMakeLists.txt.bak CMakeLists.txt", shell=True)
            process.wait()

            if not click.confirm("Do you want to keep the changes"):
                shutil.copyfile("CMakeLists.txt.bak", "CMakeLists.txt")
                os.remove("CMakeLists.txt.bak")
                return
            os.remove("CMakeLists.txt.bak")

            if click.confirm("Have you tested your changes and want to commit them now?"):
                subprocess.call("git add CMakeLists.txt", shell=True)
                subprocess.call("git commit -m 'Update CMakeLists.txt to {0}'".format(current_version), shell=True)
