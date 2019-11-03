# [![Kathará](https://github.com/KatharaFramework/Kathara/raw/master/images/logo_kathara_small.png)](http://www.kathara.org)
<p align="right">
    <a href="https://www.gnu.org/licenses/gpl-3.0"><img src="https://img.shields.io/badge/License-GPL%20v3-blue.svg" alt="License: GPL v3" target="_blank" /></a>
</p>
<ul>
    <li><a href="#installation">Installation</a></li>
    <li><a href="#graphical-user-interface">Graphical User Interface</a></li>
    <li><a href="https://github.com/KatharaFramework/Docker-Images">Docker Images and Dockerfiles</a></li>
    <li><a href="https://github.com/KatharaFramework/Kathara/wiki/Man-Pages">Man Pages</a></li>
    <li><a href="#example">Example</a></li>
    <li><a href="https://github.com/KatharaFramework/Kathara-Labs">Examples and Tutorials</a></li>
</ul>

From the Greek Καθαρά.  
Implementation of the notorious [Netkit](https://github.com/maxonthegit/netkit-core) using Python. 10 times faster than Netkit and more than 100 times lighter, allows easy configuration and deploy of arbitrary virtual networks with SDN, NFV and traditional routing protocols. The framework has the performances to run in production and our images can emulate most network equipments.

Kathará comes with **P4**, **OpenVSwitch**, **Quagga**, **Bind**, and more, but can also be extended with your own container images. For more information about Kathará images please visit the dedicated [repo](https://github.com/KatharaFramework/Docker-Images).

## Installation
Install Docker and then run the installer. For a step by step guide check the [Wiki](https://github.com/KatharaFramework/Kathara/wiki).

## Graphical User Interface

Being based on Netkit, all previous [tools](http://wiki.netkit.org/index.php/Download_Contributions) still work. 
In particular we suggest [Netkit Lab Generator](https://github.com/KatharaFramework/Netkit-Lab-Generator), a GUI that allows the easy creation of a lab configuration and the visualization of its network topology.

## Example
* Installa Kathará by following the installation steps above
* Download and unpack "BGP, OSPF and RIP interplay" from [here](https://github.com/KatharaFramework/Kathara-Labs/raw/master/Labs%20Integrating%20Several%20Technologies/BGP%2C%20OSPF%20and%20RIP%20interplay/kathara-lab_bgp-ospf-rip.zip).
* The topology of this lab can be found [here](https://github.com/KatharaFramework/Kathara-Labs/blob/master/Labs%20Integrating%20Several%20Technologies/BGP%2C%20OSPF%20and%20RIP%20interplay/kathara-lab_bgp-ospf-rip.pdf).
* `cd` inside "BGP, OSPF and RIP interplay" and run `kathara lstart`
* Kathará will read the configuration of the lab from `lab.conf`, `lab.dep` and the various `*.startup` files and start the machines, opening terminal windows to interact with the virtual network nodes.
* After you're done experimenting, simply run `kathara lclean`
* This will kill and remove all the machines.
