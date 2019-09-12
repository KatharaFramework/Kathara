FROM ubuntu:18.04

RUN apt update
RUN apt upgrade -y
RUN DEBIAN_FRONTEND=noninteractive apt install -y \
    apache2 \
    apache2-bin \
    apt-utils \
    apt-transport-https \ 
    arping \
    arptables \
    bind9 \
    bridge-utils \
    build-essential \
    curl \
    diffutils \
    dnsutils \
    dublin-traceroute \
    ethtool \
    geoip-database \
    git \
    gnupg \
    ieee-data \
    ifupdown \
    inetutils-traceroute \
    iproute2 \
    iptables \
    iputils-ping \
    iputils-tracepath \
    less \
    links \
    lsb-base \
    lsb-release \
    make \
    manpages \
    nano \
    net-tools \
    netbase \
    openssh-client \
    openssh-server \
    openssh-sftp-server \
    openssl \
    paris-traceroute \
    rsync \
    screen \
    sed \
    tar \
    tcpdump \
    telnet \
    wget \
    vim

RUN ln -s /etc/init.d/bind9 /etc/init.d/bind

RUN apt clean