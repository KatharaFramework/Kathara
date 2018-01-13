# [![Kathará](logo_kathara_small.png)](http://www.kathara.org)
<p align="right">
    <a href="https://www.gnu.org/licenses/gpl-3.0"><img src="https://img.shields.io/badge/License-GPL%20v3-blue.svg" alt="License: GPL v3" target="_blank" /></a>
</p>
<ul>
    <li><a href="#installation">Installation</a></li>
    <li><a href="#provided-docker-images">Provided Docker Images</a></li>
    <li><a href="#manual">Manual</a></li>
    <li><a href="#tools">Tools</a></li>
    <li><a href="#example">Example</a></li>
</ul>

From the Greek Καθαρά. 
Implementation of the notorious [Netkit](https://github.com/maxonthegit/netkit-core) using Python and Docker. 10 times faster than Netkit and more than 100 times lighter, allows easy configuration and deploy of arbitrary virtual networks with for SDN, NFV and traditional routing protocols. 

Kathará comes with **P4**, **OpenVSwitch**, **Quagga**, **Bind**, and more, but can also be extended with your own container images. 

Thanks to Docker, the framework has the performances to run in production and our images can emulate most network equipments.

## Installation
* To run Kathará you first need to install [Docker](https://www.docker.com/) and Python 2.x. For Linux users I suggest installing Docker from https://get.docker.com while for Windows and Mac it's easier to use https://download.docker.com. 
* Download all the files to a directory of your choice (from a [release](https://github.com/Kidel/Kathara/releases) or `git clone`). 
* Add the environment variable `NETKIT_HOME` to your system _pointing to the **bin** folder_:
  * Linux: `export NETKIT_HOME=/home/foo/kathara/bin` (you can also do this permanently by adding it to `~/.bashrc`).
  * Windows: System > Advanced settings > Environment Variables > New > ...
    * Variable name: `NETKIT_HOME`, Variable value: `DRIVE:\path\to\kathara\bin`.
    * You'll also need to share the drive that will contain the labs and the drive with your user folder (it can be done from Docker settings, from the tray icon), as shown [here](tutorial/winshare.png) (note that you may have/need different drives).
* Run the installer:
  * Linux: `$NETKIT_HOME/install` (optionally `--skip-p4` to avoid pre-downloading the P4 image, that may not be needed, and `--admin` removes the wrapper (unsafe/admin mode)). 
  * Windows: `%NETKIT_HOME%\install`(completely optional, it only pre-downloads images).
* You can optionally add NETKIT_HOME to your PATH, but the `NETKIT_HOME` variable is still required. 

## Provided Docker Images
A list of the Docker images we provided can be found at [this page](https://hub.docker.com/u/bonofiglio/) in the Docker Hub.

## Manual
The interface of Kathará is basically the same we used for Netkit, and it's available here: [Man page of NETKIT](http://wiki.netkit.org/man/man7/netkit.7.html).

The main difference is the way we specify the interfaces in the `vstart` command (now requiring `--eth 0:A --eth 1:B ...`) but why would you ever use `vstart` when you have `lstart`?

Also the subnet `172.0.0.0/8` (basically any IP starting with `172`) is reserved and should not be used when configuring links. 

## Tools
Being based on Netkit, all previous [tools](http://wiki.netkit.org/index.php/Download_Contributions) still work. 
In particular we suggest [Netkit Lab Generator](https://github.com/Kidel/Netkit-Lab-Generator), a web interface that allows the easy creation of a lab configuration and the visualization of the topology itself. 
![Netkit Lab Generator](https://raw.githubusercontent.com/Kidel/Netkit-Lab-Generator/master/images/screencapture-1460378572119.png)

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

