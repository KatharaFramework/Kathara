# [![Kathará](images/logo_kathara_small.png)](http://www.kathara.org)

<p style="float:right">
    <a href="https://www.gnu.org/licenses/gpl-3.0"><img src="https://img.shields.io/badge/License-GPL%20v3-blue.svg" alt="License: GPL v3" target="_blank" /></a>
</p>

# About
Kathará takes its name from the Greek word Καθαρά. It is the implementation of the notorious [Netkit](https://github.com/maxonthegit/netkit-core) using Python and Docker. 

10 times faster than Netkit and more than 100 times lighter, allows easy configuration and deploy of arbitrary virtual networks with for SDN, NFV and traditional routing protocols. It comes with **P4**, **OpenVSwitch**, **Quagga**, **Bind**, and more, but can also be extended with your own container images. 

Thanks to Docker, the framework has the performances to run in production and our images can emulate most network equipments.

# Index
* [Installation](#installation)
  * [Linux](#linux)
  * [Windows](#windows)
  * [Mac](#mac)
* [Instructions](#instructions)
  * [Example](#example)
  * [Graphical User Interface](#graphical-user-interface)
* [More](#more)
  * [Provided Docker Images](#provided-docker-images)
  * [Extend Kathará](#extend-kathará)

# Installation

## Linux
* Install [**Docker**](https://www.docker.com/).
  * We suggest installing Docker from [this script](https://get.docker.com).
  * We suggest adding your user to the docker group with `sudo usermod -aG docker <username>`.
* Install **Python 2.x**.
  * It should be pre-installed on most Linux distributions; if it isn't, you can get it from [here](https://www.python.org/downloads).
* Install **gcc** (you may need it to install the wrapper) by simply running `sudo apt-get install build-essential`.
* (suggested) Install **xterm** terminal emulator (usually `sudo apt-get install xterm`).
  * You can also specify a different terminal emulator by using the `--xterm=...` command parameter while starting a network node or a lab.
  * It is also possible to avoid opening new terminals at all by using `--noterminals`.
* Download all the files to a directory of your choice.
  * Either download from a [release](https://github.com/Kidel/Kathara/releases) or by console with `git clone --recursive https://github.com/Kidel/Kathara.git`). 
* Add the environment variable `NETKIT_HOME` to your system pointing to the **bin** folder:
  * `export NETKIT_HOME=/home/foo/kathara/bin`
  * (you can also do this permanently by adding it to `~/.bashrc`).
* Run the installer with `$NETKIT_HOME/install` (it will create the configuration file and download the images).
  * (you can optionally use `--skip-p4` option to avoid pre-downloading the P4 image, that may not be needed, and `--admin` removes the wrapper (will require sudo)). 
* (suggested) You can add NETKIT_HOME to your PATH, but the `NETKIT_HOME` variable is still required. 

## Windows
* Install [Docker](https://www.docker.com/)
  * You can get it from [here](https://www.docker.com/community-edition#/download) or from [here](https://download.docker.com).
  * **NB**: On Windows 8 x64 and 10 x64 this will also download and enable Hyper-V. If you later want to use another hypervisor like VMware or Virtual Box, than you will have to disable Hyper-V and restart your PC. If you later need to use Docker or Kathará again, you'll have to re-enable Hyper-V and restart.
* Install Python 2.x.
  * You can get it from [here](https://www.python.org/downloads).
* Add the environment variable `NETKIT_HOME` to your system pointing to the **bin** folder:
 * System > Advanced settings > Environment Variables > New > ...
    * Variable name: `NETKIT_HOME`, Variable value: `DRIVE:\path\to\kathara\bin`.
    * You'll also need to share the drive that will contain the labs and the drive with your user folder (it can be done from Docker settings, from the tray icon), as shown [here](images/winshare.png) (note that you may have/need different drives).
* Run the installer with `%NETKIT_HOME%\install` (it will create the configuration file and download the images).
* (suggested) You can add NETKIT_HOME to your PATH, but the `NETKIT_HOME` variable is still required.
* Remember to run Docker before using Kathará.

## Mac
* Install [Docker](https://www.docker.com/)
  * You can get it from [here](https://www.docker.com/community-edition#/download) or from [here](https://download.docker.com).
* Install Python 2.x.
  * You can get it from [here](https://www.python.org/downloads).
* (suggested) Install [XQuartz](https://www.xquartz.org/) to get **xterm** terminal emulator, that is used by default.
  * You can also specify a different terminal emulator by using the `--xterm=...` command parameter while starting a network node or a lab.
  * It is also possible to avoid opening new terminals at all by using `--noterminals`.
* Download all the files to a directory of your choice.
  * Etirher download from a [release](https://github.com/Kidel/Kathara/releases) or by console with `git clone --recursive https://github.com/Kidel/Kathara.git`). 
* Add the environment variable `NETKIT_HOME` to your system pointing to the **bin** folder:
  * `export NETKIT_HOME=/Users/<YOUR_USER_HOME>/kathara/bin`
  * (you can also do this permanently by adding it to `~/.bash_profile`).
* Run the installer with `$NETKIT_HOME/install --admin`
  * (you can optionally use `--skip-p4` option to avoid pre-downloading the P4 image, that may not be needed). 
  * Ignore any warning related to user groups.
  * **NB**: Please be aware that `--admin` is mandatory on Mac and you also don't need a wrapper since Docker works from inside an hypervisor. There is also no need to share drives, since the user folder is already shared with the hypervisor by default.
* (suggested) You can add NETKIT_HOME to your PATH, but the `NETKIT_HOME` variable is still required. 
* Remember to run Docker before using Kathará.

# Instructions
The interface of Kathará is basically the same we used for Netkit, and it's available here: [Man page of NETKIT](http://wiki.netkit.org/man/man7/netkit.7.html).

Here are some  differences with Netkit:
* When we specify the interfaces in the `vstart` command, the syntax is now the following one: `--eth 0:A --eth 1:B ... <machine-name>`). But why would you ever use `vstart` when you have `lstart`? However an example for the new syntax of vstart may be: `vstart --eth 0:A --eth 1:B pc1` where "pc1" is the name of the network node to be started. 
* There is a new l-command, `lwipe`, that erases every container and network created by Kathará, including its cache. 
* The subnet `172.0.0.0/8` (basically any IP starting with `172`) is reserved and **should not be used when configuring links**.

For `ltest`there are 2 minor adjustments:
* `--verify` needs to be followed by `=` before the option (e.g. `ltest --verify=user`).
* `--script-mode` has been replaced by simply sending stdout to `/dev/null` (e.g. `ltest --verify=user &> /dev/null`).

## Example
* Installa Kathará by following the installation steps above
* Download and unpack MARACAS_lab from [here](http://wiki.netkit.org/netkit-labs/netkit-labs_exams/icn-20151120/icn-20151120.tar.gz).
  * The topology of this lab can be found [here](http://wiki.netkit.org/netkit-labs/netkit-labs_exams/icn-20151120/icn-20151120.pdf).
* `cd` inside MARACAS_lab and run `lstart`:
  * Linux: `$NETKIT_HOME/lstart`
  * Windows: `%NETKIT_HOME%\lstart`
* Kathará will read the configuration of the lab from `lab.conf`, `lab.dep` and the various `*.startup` files and start the containers, opening terminal windows to interact with the virtual network nodes.
* After you're done experimenting, simply run `lclean`:
  * Linux: `$NETKIT_HOME/lclean`
  * Windows: `%NETKIT_HOME%\lclean`
* This will kill and remove any container.

## Graphical User Interface

Being based on Netkit, all previous [tools](http://wiki.netkit.org/index.php/Download_Contributions) still work. 
In particular we suggest [Netkit Lab Generator](https://github.com/Kidel/Netkit-Lab-Generator), a GUI that allows the easy creation of a lab configuration and the visualization of its network topology.

![Netkit Lab Generator](https://raw.githubusercontent.com/Kidel/Netkit-Lab-Generator/master/images/screencapture-201801143.png)

You can download both Kathará and the GUI by cloning recursively using `git clone --recursive https://github.com/Kidel/Kathara.git` or by downloading the pre-compiled version from the [releases page](https://github.com/Kidel/Kathara/releases) page.

# More
## Provided Docker Images
A list of the Docker images we provided can be found at [this page](https://hub.docker.com/u/kathara/) in the Docker Hub.

## Extend Kathará
Extending Kathará is actually very simple. Any local or remote Docker image tagged as `kathara/IMAGENAME` can be used with `vstart --image=IMAGENAME --eth=0:A node_name` or with `lstart` having something like that in `lab.conf`: `node_name[image]=IMAGENAME`.

To alter (locally) an existing Kathará image refer to the following steps.
1. `docker pull kathara/netkit_base` (or `kathara/p4`)
2. `docker run -tid --name YOUR_NEW_NAME kathara/netkit_base`
3. `docker exec -ti  YOUR_NEW_NAME bash`
4. Do your thing, then exit.
5. `docker commit YOUR_NEW_NAME  kathara/YOUR_NEW_NAME`
6. `docker rm -f YOUR_NEW_NAME`

<hr>

## TODO
* Components and configuration checker.
* Better and more informative installer.
