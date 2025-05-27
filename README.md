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
    <li><a href="#publications-and-presentations">Publications</a></li>
    <li><a href="#external-tools">External Tools</a></li>
    <li><a href="#success-stories">Success Stories</a></li>
    <li><a href="#join-us">Join Us</a></li>
    <li><a href="https://github.com/KatharaFramework/Docker-Images">Docker Images and Dockerfiles</a></li>
    <li><a href="https://github.com/KatharaFramework/Kathara-Labs">Examples and Tutorials</a></li>
    <li><a href="https://github.com/KatharaFramework/Kathara-Labs/tree/main/tutorials/python-api">Python APIs</a></li>
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
Install Docker and then run the installer specific for your Operating System. For a step-by-step guide check the [Wiki](https://github.com/KatharaFramework/Kathara/wiki).

For further information on how to use Kathará on Kubernetes (**Megalos**) please refer to the [Wiki Page](https://github.com/KatharaFramework/Kathara/wiki/Megalos-(Kathara-over-Kubernetes)).

Kathará also provides a set of Python APIs.
See the [Python APIs Tutorial](https://github.com/KatharaFramework/Kathara-Labs/tree/main/tutorials/python-api) and the [docs](https://github.com/KatharaFramework/Kathara/wiki/Kathara-API-Docs).

## Quick Example
<p align="center">
    <img width="100%" src="https://raw.githubusercontent.com/wiki/KatharaFramework/Kathara/lstart-example.gif" />
</p>

* Install Kathará by following the Installation section.
* Download and unpack the network scenario of a "Small Internet" from [here](https://github.com/KatharaFramework/Kathara-Labs/blob/main/main-labs/labs-integrating-several-technologies/small-internet-with-dns-and-web-server/kathara-lab_small-internet-with-dns-and-web-server.zip) 
(network topology can be found [here](https://github.com/KatharaFramework/Kathara-Labs/blob/main/main-labs/labs-integrating-several-technologies/small-internet-with-dns-and-web-server/kathara-lab_small-internet-with-dns-and-web-server.pdf)).
* `cd` inside `small-internet-with-dns-webserver` and run `kathara lstart`.
* Kathará will read the configuration of the scenario from `lab.conf` and the various `*.startup` files and start the devices, opening terminal windows to interact with them.
* After you're done experimenting, simply run `kathara lclean` and wait until the network scenario closes.

## Publications and Presentations
Kathará is developed by [Roma Tre Computer Networks and Security Research Group](https://compunet.ing.uniroma3.it/). 

Several publications are related to the tool:
- <a href="https://ieeexplore.ieee.org/abstract/document/8406267/" target="_blank"> **Kathará: A container-based framework for implementing network function virtualization and software defined networks**</a> (at NOMS 2018)
  - <a href="https://www.slideshare.net/GaetanoBonofiglio/kathar-noms-2018-106743047" target="_blank">Presentation</a>
- <a href="https://ieeexplore.ieee.org/document/9110288" target="_blank"> **Megalos: A Scalable Architecture for the Virtualization of Network Scenarios** </a> (at NOMS 2020)
  - <a href="https://www.youtube.com/watch?v=XvInh-kujrA" target="_blank">Presentation</a>
- <a href="https://ieeexplore.ieee.org/document/9110351" target="_blank"> **Kathará: A Lightweight Network Emulation System** </a> (at NOMS 2020)
  - <a href="https://www.youtube.com/watch?v=ionEpKjv3Vk" target="_blank">Presentation</a>
  - <a href="https://www.kathara.org/assets/images/awards/NOMS2020_TPC_awards_signed.V2_Page_2_%20Best%20Nemo%20.jpg" target="_blank">Best Demo Paper Award</a>
- <a href="https://www.mdpi.com/1999-5903/13/9/227" target="_blank"> **Megalos: A Scalable Architecture for the Virtualization of Large Network Scenarios** </a> (in MDPI Future Internet Journal 2021)
- <a href="https://ieeexplore.ieee.org/document/9789876">**Sibyl: a Framework for Evaluating the Implementation of Routing Protocols in Fat-Trees**</a> (at NOMS 2022)
  - <a href="https://www.youtube.com/watch?v=FZjHjLZzXCY">NOMS2022 Presentation</a>
  - <a href="https://www.youtube.com/watch?v=FfjdqP8eKW8&t=3376s">RTGWG Session at IETF114</a>

Kathará has been also presented in meetings and workshops:
- <a href="https://datatracker.ietf.org/meeting/interim-2020-rift-01/materials/slides-interim-2020-rift-01-sessa-tools-for-experimenting-routing-in-dc-00" target="_blank">RIFT Working Group Meeting</a> (IETF 107 - March 2020)
- <a href="https://www.youtube.com/watch?v=GVBOdNzwhBA" target="_blank">Kathará: A Lightweight Network Emulation System (Italian Audio)</a> (GraphRM - June 2022)
- <a href="https://ripe85.ripe.net/archives/video/941/" target="_blank">Kathará: A Lightweight and Scalable Network Emulation System</a> (RIPE 85 - October 2022)

## External Tools

- [Netkit Lab Generator](https://github.com/KatharaFramework/Netkit-Lab-Generator), a GUI that allows the easy creation of a network scenario configuration and the visualization of its network topology.
- [VFTGen](https://github.com/KatharaFramework/VFTGen), a tool that allows creating three levels Fat Tree topologies (single-plane or multi-planes) and automatically configure them to run on Kathará.
- [Tacatá](https://github.com/damiano-massarelli/Tacata), a lightweight Python script which creates Netkit and Kathará labs using an enriched version of the lab.conf file with a simple syntax.
- [net-vis](https://github.com/Friscobuffo/net-vis-localhost), a tool that parses (and generates) the `lab.conf` file and all the `.startup` files to visualize the network.
- [kathara-lab-starter](https://github.com/BuonHobo/kathara-lab-starter), an easy and extensible tool to get a kathara lab started.  Utilizing JSON input files, it accelerates setup, while minimizing configuration redundancies.
- [NetGUI-Kathará](https://gitlab.com/eva.castro/netgui-kathara), NetGUI-Kathará is a graphical interface for Kathará that lets users design and manage network topologies. It also generates files for 3D traffic visualization with [WireXRk](https://pheras.gitlab.io/wirexrk/).

## Success Stories
As far as we know, Kathará is currently being used in many [courses and projects](https://www.kathara.org/stories.html). 
 
We encourage you to tell us your story! 

We are also collecting network scenarios from the community. If you want to be added to the [list](https://github.com/KatharaFramework/Kathara-Labs/tree/main/community-labs), please contact us!

## Join Us

Kathará is an open source project. 
Feel free to download the code, play with it, and submit feature requests, notify bugs, or open pull requests!

Thanks to everyone who has contributed to the development of Kathará!
