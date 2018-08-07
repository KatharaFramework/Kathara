# [![Kathará](images/logo_kathara_small.png)](http://www.kathara.org)
<p align="right">
    <a href="https://www.gnu.org/licenses/gpl-3.0"><img src="https://img.shields.io/badge/License-GPL%20v3-blue.svg" alt="License: GPL v3" target="_blank" /></a>
</p>
<ul>
    <li><a href="#graphical-user-interface">Graphical User Interface</a></li>
    <li><a href="#installation">Installation</a>
        <ul>
            <li><a href="#linux">Linux</a></li>
            <li><a href="#windows">Windows</a></li>
            <li><a href="#mac">Mac</a></li>
        </ul>
    </li>
    <li><a href="#provided-docker-images">Provided Docker Images</a></li>
    <li><a href="#manual">Manual</a></li>
    <li><a href="#example">Example</a></li>
    <li><a href="#extend-kathará">Extend Kathará</a></li>
</ul>

From the Greek Καθαρά. 
Implementation of the notorious [Netkit](https://github.com/maxonthegit/netkit-core) using Python and Docker. 10 times faster than Netkit and more than 100 times lighter, allows easy configuration and deploy of arbitrary virtual networks with for SDN, NFV and traditional routing protocols. 

Kathará comes with **P4**, **OpenVSwitch**, **Quagga**, **Bind**, and more, but can also be extended with your own container images. 

Thanks to Docker, the framework has the performances to run in production and our images can emulate most network equipments.

## Graphical User Interface
You can download both Kathará and the GUI by cloning recursively using 
* `git clone --recursive https://github.com/Kidel/Kathara.git`

Or by downloading the **pre-compiled** version from the [releases](https://github.com/Kidel/Kathara/releases) page.

Being based on Netkit, all previous [tools](http://wiki.netkit.org/index.php/Download_Contributions) still work. 
In particular we suggest [Netkit Lab Generator](https://github.com/Kidel/Netkit-Lab-Generator), a GUI that allows the easy creation of a lab configuration and the visualization of its network topology.
![Netkit Lab Generator](https://raw.githubusercontent.com/Kidel/Netkit-Lab-Generator/master/images/screencapture-201801143.png)

## Installation

### Linux
* Install [Docker](https://www.docker.com/). We suggest installing Docker from [this script](https://get.docker.com).
* Install Python 2.x. It should be pre-installed on most Linux distributions; if it isn't, you can get it from [here](https://www.python.org/downloads).
* You may need gcc to install the wrapper, simply run `apt-get install build-essential`
* (suggested) Install **xterm** terminal emulator (usually `sudo apt-get install xterm`), that is used by default. You can also specify a different terminal emulator by using the `--xterm=...` command parameter while starting a network node or a lab. It is also possible to avoid opening new terminals at all by using `--noterminals`.
* Download all the files to a directory of your choice (from a [release](https://github.com/Kidel/Kathara/releases) or `git clone --recursive https://github.com/Kidel/Kathara.git`). 
* Add the environment variable `NETKIT_HOME` to your system _pointing to the **bin** folder_:
  * `export NETKIT_HOME=/home/foo/kathara/bin` (you can also do this permanently by adding it to `~/.bashrc`).
* Run the installer:
  * `$NETKIT_HOME/install` (optionally `--skip-p4` to avoid pre-downloading the P4 image, that may not be needed, and `--admin` removes the wrapper (will require sudo)). 
* You can optionally add NETKIT_HOME to your PATH, but the `NETKIT_HOME` variable is still required. 

### Windows
* Install [Docker](https://www.docker.com/) from [here](https://www.docker.com/community-edition#/download) or [here](https://download.docker.com).
  * **NB**: On Windows 8 x64 and 10 x64 this will also download and enable Hyper-V. If you later want to use another hypervisor like VMware or Virtual Box, than you will have to disable Hyper-V and restart your PC. If you later need to use Docker or Kathará again, you'll have to re-enable Hyper-V and restart. **Also this will require that Virtualization technology is enabled in your system BIOS. It is also highly suggested to enable virtualization on BIOS and Windows before trying to install Docker**.
  * For more information and an example check out [this document](https://github.com/Kidel/Kathara/blob/master/doc/HyperV.pdf).
* Install Python 2.x. You can get it from [here](https://www.python.org/downloads). Make sure that Python is added to your PATH variable. 
* Add the environment variable `NETKIT_HOME` to your system _pointing to the **bin** folder_:
  * System > Advanced settings > Environment Variables > New > ...
    * Variable name: `NETKIT_HOME`, Variable value: `DRIVE:\path\to\kathara\bin`.
    * You'll also need to share the drive that will contain the labs and the drive with your user folder (it can be done from Docker settings, from the tray icon), as shown [here](images/winshare.png) (note that you may have/need different drives).
* Run the installer:
  * `%NETKIT_HOME%\install`(it will create the configuration file and download the images).
* You can optionally add NETKIT_HOME to your PATH, but the `NETKIT_HOME` variable is still required.
* Remember to run Docker before using Kathará.

### Mac
* Install [Docker](https://www.docker.com/) from [here](https://www.docker.com/community-edition#/download) or [here](https://download.docker.com).
* Install Python 2.x. You can get it from [here](https://www.python.org/downloads).
* (suggested) Install [XQuartz](https://www.xquartz.org/) to get **xterm** terminal emulator, that is used by default. You can also specify a different terminal emulator by using the `--xterm=...` command parameter while starting a network node or a lab. It is also possible to avoid opening new terminals at all by using `--noterminals`.
* Download all the files to a directory of your choice (from a [release](https://github.com/Kidel/Kathara/releases) or `git clone --recursive https://github.com/Kidel/Kathara.git`). 
* Add the environment variable `NETKIT_HOME` to your system _pointing to the **bin** folder_:
  * `export NETKIT_HOME=/Users/<YOUR_USER_HOME>/kathara/bin` (you can also do this permanently by adding it to `~/.bash_profile`).
* Run the installer:
  * `$NETKIT_HOME/install --admin` (optionally `--skip-p4` to avoid pre-downloading the P4 image, that may not be needed). Ignore any warning related to user groups and please be aware that `--admin` is mandatory on Mac and you also don't need a wrapper since Docker works from inside an hypervisor. There is also no need to share drives, since the user folder is already shared with the hypervisor by default. 
* You can optionally add NETKIT_HOME to your PATH, but the `NETKIT_HOME` variable is still required.
* Remember to run Docker before using Kathará.

## Provided Docker Images
A list of the Docker images we provided can be found at [this page](https://hub.docker.com/u/kathara/) in the Docker Hub.

## Manual
The interface of Kathará is basically the same we used for Netkit, and it's available here: [Man page of NETKIT](http://wiki.netkit.org/man/man7/netkit.7.html).

The main difference is the way we specify the interfaces in the `vstart` command (now requiring `--eth 0:A --eth 1:B ...`) but why would you ever use `vstart` when you have `lstart`? However an example for the syntax of vstart now may be: `vstart --eth 0:A --eth 1:B pc1` where "pc1" is the name of the network node to be started. 

In addition there is another command, `lwipe`, that erases every container and network created by Kathará, including its cache. 

Also the subnet `172.0.0.0/8` (basically any IP starting with `172`) is reserved and should not be used when configuring links. 

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

## Extend Kathará
Extending Kathará is actually very simple. Any local or remote Docker image tagged as `kathara/IMAGENAME` can be used with `vstart --image=IMAGENAME --eth=0:A node_name` or with `lstart` having something like that in `lab.conf`: `node_name[image]=IMAGENAME`.

To alter (locally) an existing Kathará image refer to the following steps (remember that, by default, Docker needs root or sudo on Linux).
1. `docker pull kathara/netkit_base` (or `kathara/p4`)
2. `docker run -tid --name YOUR_NEW_NAME kathara/netkit_base`
3. `docker exec -ti  YOUR_NEW_NAME bash`
4. Do your thing, then exit.
5. `docker commit YOUR_NEW_NAME  kathara/YOUR_NEW_NAME`
6. `docker rm -f YOUR_NEW_NAME`


## TODO
* Components and configuration checker.
* Better and more informative installer.
