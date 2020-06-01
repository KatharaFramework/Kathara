FROM debian:10

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
    bison \
    bridge-utils \
    build-essential \
    curl \
    diffutils \
    dnsutils \
    dublin-traceroute \
    ethtool \
    expect \
    flex \
    geoip-database \
    git \
    gnupg \
    ieee-data \
    ifupdown \
    inetutils-traceroute \
    iptables \
    iputils-ping \
    iputils-tracepath \
    less \
    links \
    lsb-base \
    lsb-release \
    make \
    man \
    nano \
    net-tools \
    netbase \
    openssh-client \
    openssh-server \
    openssh-sftp-server \
    openssl \
    paris-traceroute \
    pkg-config \
    rsync \
    screen \
    sed \
    tar \
    tcpdump \
    telnet \
    wget \
    vim


RUN apt clean

RUN ln -s /etc/init.d/bind9 /etc/init.d/bind

COPY .bashrc /root/.bashrc

WORKDIR /

VOLUME /hosthome
VOLUME /shared
