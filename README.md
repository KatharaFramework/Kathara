# [![Kathará](images/logo_kathara_small.png)](http://www.kathara.org)
<p align="right">
    <a href="https://www.gnu.org/licenses/gpl-3.0"><img src="https://img.shields.io/badge/License-GPL%20v3-blue.svg" alt="License: GPL v3" target="_blank" /></a>
</p>
<ul>
    <li><a href="#installation">Installation</a></li>
    <li><a href="#graphical-user-interface">Graphical User Interface</a></li>
    <li><a href="#provided-docker-images">Provided Docker Images</a></li>
    <li><a href="#manual">Manual</a></li>
    <li><a href="#example">Example</a></li>
    <li><a href="https://github.com/KatharaFramework/Kathara-Labs">More Examples and Guides</a></li>
    <li><a href="#extend-kathará">Extend Kathará</a></li>
</ul>

From the Greek Καθαρά. 
Implementation of the notorious [Netkit](https://github.com/maxonthegit/netkit-core) using Python and Docker. 10 times faster than Netkit and more than 100 times lighter, allows easy configuration and deploy of arbitrary virtual networks with for SDN, NFV and traditional routing protocols. 

Kathará comes with **P4**, **OpenVSwitch**, **Quagga**, **Bind**, and more, but can also be extended with your own container images. 

Thanks to Docker, the framework has the performances to run in production and our images can emulate most network equipments.

## Installation
Install Docker and Python 2.x and then run the installer. For a step by step guide check the [Wiki](https://github.com/KatharaFramework/Kathara/wiki).

## Graphical User Interface
You can download both Kathará and the GUI by cloning recursively using 
* `git clone --recursive https://github.com/KatharaFramework/Kathara.git`

Or by downloading the **pre-compiled** version from the [releases](https://github.com/KatharaFramework/Kathara/releases) page.

Being based on Netkit, all previous [tools](http://wiki.netkit.org/index.php/Download_Contributions) still work. 
In particular we suggest [Netkit Lab Generator](https://github.com/KatharaFramework/Netkit-Lab-Generator), a GUI that allows the easy creation of a lab configuration and the visualization of its network topology.
![Netkit Lab Generator](https://raw.githubusercontent.com/KatharaFramework/Netkit-Lab-Generator/master/images/screencapture-201801143.png)

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

### More examples and guides can be found [here](https://github.com/KatharaFramework/Kathara-Labs).

## Extend Kathará
Extending Kathará is actually very simple. Any local or remote Docker image tagged as `kathara/IMAGENAME` can be used with `vstart --image=IMAGENAME --eth=0:A node_name` or with `lstart` having something like that in `lab.conf`: `node_name[image]=IMAGENAME`.

If your Docker image uses a different shell instead of `bash` you can change it in `vstart` by using the extra flag `--shell=SHELLNAME` or in lstart by editing your `lab.conf` accordingly (e.g.: `node_name[shell]=SHELLNAME`).

To alter (locally) an existing Kathará image refer to the following steps (remember that, by default, Docker needs root or sudo on Linux).
1. `docker pull kathara/netkit_base` (or `kathara/p4`)
2. `docker run -tid --name YOUR_NEW_NAME kathara/netkit_base`
3. `docker exec -ti  YOUR_NEW_NAME bash`
4. Do your thing, then exit.
5. `docker commit YOUR_NEW_NAME  kathara/YOUR_NEW_NAME`
6. `docker rm -f YOUR_NEW_NAME`

