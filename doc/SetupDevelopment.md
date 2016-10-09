# Development Setup for the MRT tools
You cat setup the MRT tools in a virtual environment. This way, it won't conflict with your system wide installation and you can easily test your modifications to the code base.

## Requirements
Install the `virtualenvwrapper` for easier handling of virtual environments and other deps
```bash
sudo apt-get install virtualenvwrapper libffi-dev libkrb5-dev libyaml-dev
source /usr/share/virtualenvwrapper/virtualenvwrapper.sh # Can be put into bashrc
```

For automatic code formatting, clang-format-3.8 is needed. To install it, follow the instructions on this site: http://apt.llvm.org/  
e.g. for Ubuntu 16.04:
```bash
echo "deb http://apt.llvm.org/xenial/ llvm-toolchain-xenial main
deb-src http://apt.llvm.org/xenial/ llvm-toolchain-xenial main
# 3.8
deb http://apt.llvm.org/xenial/ llvm-toolchain-xenial-3.8 main
deb-src http://apt.llvm.org/xenial/ llvm-toolchain-xenial-3.8 main
# 3.9
deb http://apt.llvm.org/xenial/ llvm-toolchain-xenial-3.9 main
deb-src http://apt.llvm.org/xenial/ llvm-toolchain-xenial-3.9 main" | sudo tee /etc/apt/sources.list.d/llvm.list
wget -O - http://apt.llvm.org/llvm-snapshot.gpg.key|sudo apt-key add -
sudo apt update
sudo apt install clang-format-3.8
```

## Creating the virtualenv and installation
First, create a new virtual environment
```bash
mkvirtualenv mrt --system-site-packages
```
You will see a `(mrt)` at the beginning of your prompt, indicating that you are working in your virtualenv.
You can deactivate it with `deactivate`. To work in this environment again use the command `workon mrt`.

Setup the mrt_tools package
```bash
python setup.py install
```

You will now be able to use the development version, whenever your virtualenv is activated.
If you want to permanently use them, you can create a link to the executable and extend your path (the export command should go into your `.bashrc`):
```bash
mkdir -p  ~/.local/bin
ln -s ~/.virtualenvs/mrt/bin/mrt ~/.local/bin/mrt
export PATH=~/.local/bin:$PATH
```
## Updating
When you want to update your MRT tools, follow these steps in the build repo:
```bash
git pull
workon mrt
pip uninstall mrt
python setup.py install
```

## Deinstallation / start from scratch
Simply remove the virtual environment:
```bash
deactivate
rmvirtualenv mrt
```
