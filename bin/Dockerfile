# Docker file for building a the Netkit image
FROM ubuntu:rolling
MAINTAINER Gabriele Lospoto <lospoto@dia.uniroma3.it>
RUN apt-get update && apt-get -y install python python-pip python-setuptools python-pbr python-bottle python-daemon python-netaddr python-twisted git openssh-server quagga tcpdump vim telnet iputils-ping inetutils-traceroute screen net-tools bind9 apache2 apache2-utils arping arptables openvswitch-switch apt-utils dialog links

# Create soft link for backward compatibility
#WORKDIR /etc
#RUN mv quagga zebra
#RUN ln -s zebra /etc/quagga

# Create soft link for backward compatibility
WORKDIR /etc/init.d
RUN ln -s quagga /etc/init.d/zebra

WORKDIR /

# Install Ryu framework
RUN pip install --upgrade pip
RUN pip install ryu

