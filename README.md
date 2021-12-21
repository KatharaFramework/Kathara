<p align="center">
    <a href="https://www.kathara.org">
        <img src="https://github.com/KatharaFramework/Kathara/wiki/logo_kathara_small.png" alt="Kathará" />
    </a>
</p>
<p align="right">
    <a href="https://github.com/KatharaFramework/Kathara/releases"><img src="https://img.shields.io/github/v/release/KatharaFramework/Kathara" /></a>
    <a href="https://github.com/KatharaFramework/Kathara/releases"><img src="https://img.shields.io/github/release-date/KatharaFramework/Kathara" /></a>
    <a href="https://github.com/KatharaFramework/Kathara/releases"><img src="https://img.shields.io/github/downloads/KatharaFramework/Kathara/total" /></a>
    <a href="https://github.com/KatharaFramework/Kathara/stargazers"><img src="https://img.shields.io/github/stars/KatharaFramework/Kathara" /></a>
    <a href="https://github.com/KatharaFramework/Kathara/blob/master/LICENSE"><img src="https://img.shields.io/github/license/KatharaFramework/Kathara" alt="License: GPL v3" target="_blank" /></a>
</p>
<ul>
    <li><a href="https://www.kathara.org">Official Website</a></li>
    <li><a href="#what-is-it">What is it?</a></li>
    <li><a href="#how-does-it-work">How does it work?</a></li>
    <li><a href="#installation">Installation</a></li>
    <li><a href="#quick-example">Quick Example</a></li>
    <li><a href="#publications">Publications</a></li>
    <li><a href="#external-tools">External Tools</a></li>
    <li><a href="#success-stories">Success Stories</a></li>
    <li><a href="#join-us">Join Us</a></li>
    <li><a href="https://github.com/KatharaFramework/Docker-Images">Docker Images and Dockerfiles</a></li>
    <li><a href="https://github.com/KatharaFramework/Kathara-Labs/wiki">Examples and Tutorials</a></li>
    <li><a href="https://github.com/KatharaFramework/Kathara/wiki/Kathara-Python-API">Python APIs</a></li>
    <li><a href="https://www.kathara.org/man-pages/kathara.1.html">Man Pages</a></li>
</ul>

## What is it?
**Kathará** (from the Greek Καθαρά, _purely_) is a lightweight network emulation system based on Docker containers.
It can be really helpful in showing interactive demos/lessons, testing production networks in a sandbox environment, or developing new network protocols.

Kathará is the spiritual successor of the notorious [Netkit](https://www.netkit.org/), hence it is cross-compatible, and inherits its language and features.

## How does it work?

Each network device is emulated by a container. 
Virtual network devices are interconnected by virtual L2 LANs.

Each container can potentially run a different Docker image. Built-in images include **Quagga**, **FRRouting**, **Bind**, **P4**, **OpenVSwitch**, and more, but you can also use your own container images.
For more information about Kathará images please visit the dedicated [repository](https://github.com/KatharaFramework/Docker-Images).

Kathará extremely simplifies the creation of complex networks using the concept of **network scenario**: a directory containing a file with the network topology, and, foreach device, files and folders containing the configuration of that device.

Kathará emulates network scenarios using either Docker or Kubernetes as backend virtualization system.

## Installation
Install Docker and then run the installer specific for your Operating System. For a step by step guide check the [Wiki](https://github.com/KatharaFramework/Kathara/wiki).

For further information on how to use Kathará on Kubernetes please refer to the [Wiki Page](https://github.com/KatharaFramework/Kathara/wiki/Megalos-(Kathara-over-Kubernetes)).

Kathará provides also a set of Python APIs.
See the [Python APIs Tutorial](https://github.com/KatharaFramework/Kathara/wiki/Kathara-Python-API) and the [docs](https://github.com/KatharaFramework/Kathara/wiki/Kathara-API-Docs).

## Quick Example
<p align="center">
    <img width="100%" src="https://raw.githubusercontent.com/wiki/KatharaFramework/Kathara/lstart-example.gif" />
</p>

* Install Kathará by following the Installation section.
* Download and unpack the network scenario of a "Small Internet" from [here](https://github.com/KatharaFramework/Kathara-Labs/raw/master/Labs%20Integrating%20Several%20Technologies/Small%20Internet%20with%20DNS%20and%20Webserver/small-internet-w-dns-webserver.zip) (network topology can be found [here](https://github.com/KatharaFramework/Kathara-Labs/blob/master/Labs%20Integrating%20Several%20Technologies/Small%20Internet%20with%20DNS%20and%20Webserver/Small%20Internet%20with%20DNS%20and%20Webserver.pdf)).
* `cd` inside `small-internet-w-dns-webserver` and run `kathara lstart`.
* Kathará will read the configuration of the scenario from `lab.conf` and the various `*.startup` files and start the devices, opening terminal windows to interact with them.
* After you're done experimenting, simply run `kathara lclean` and wait until the network scenario closes.

## Publications 
Kathará is developed by [Roma Tre Computer Networks and Security Research Group](https://compunet.ing.uniroma3.it/). 
Several publications are related to this tool:

- <a href="https://ieeexplore.ieee.org/abstract/document/8406267/" target="_blank"> **Kathará: A container-based framework for implementing network function virtualization and software defined networks**</a> (at NOMS 2018)
    - <a href="https://www.slideshare.net/GaetanoBonofiglio/kathar-noms-2018-106743047" target="_blank">Presentation</a>
- <a href="https://ieeexplore.ieee.org/document/9110288" target="_blank"> **Megalos: A Scalable Architecture for the Virtualization of Network Scenarios** </a> (at NOMS 2020)
    - <a href="https://www.youtube.com/watch?v=XvInh-kujrA&amp;feature=youtu.be" target="_blank">Presentation</a>
- <a href="https://ieeexplore.ieee.org/document/9110351" target="_blank"> **Kathará: A Lightweight Network Emulation System** </a> (at NOMS 2020) 
    - <a href="https://www.youtube.com/watch?v=ionEpKjv3Vk&amp;feature=youtu.be" target="_blank">Presentation</a>
    - <a href="https://noms2020.ieee-noms.org/sites/noms2020.ieee-noms.org/files/NOMS2020_TPC_awards_signed.V2_Page_2_%20Best%20Nemo%20.jpg" target="_blank">Best Demo Paper Award</a>
- <a href="https://www.mdpi.com/1999-5903/13/9/227" target="_blank"> **Megalos: A Scalable Architecture for the Virtualization of Large Network Scenarios** </a> (at Future Internet 2021)

## External Tools

- [Netkit Lab Generator](https://github.com/KatharaFramework/Netkit-Lab-Generator), a GUI that allows the easy creation of a network scenario configuration and the visualization of its network topology.
- [VFTGen](https://github.com/KatharaFramework/VFTGen), a tool that allows to create three levels Fat Tree topologies (single-plane or multi-planes) and automatically configure them to run on Kathará.

Being based on Netkit, all the previous tools still work. 

## Success Stories
As far as we know, Kathará is currently being used in many [courses and projects](https://www.kathara.org/stories.html). 
 
We encourage you to tell us your story! 

We are also collecting network scenarios from the community. If you wanto to be added to the [list](https://github.com/KatharaFramework/Kathara-Labs/wiki/Community-Labs), please contact us!

## Join Us

Kathará is an open source project. 
Feel free to download the code, play with it, and submit feature requests, notify bugs, or open pull requests!

Thanks to everyone who has contributed to the development of Kathará!
