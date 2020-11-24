FROM archlinux:latest

RUN pacman -Syyu --noconfirm
RUN pacman-db-upgrade

RUN useradd -m -s /bin/bash builduser && \
	usermod -G users builduser 

RUN pacman -S --noconfirm git \
				 base-devel \
				 python-pip \
				 ruby 

ENV RUBYOPT="-KU -E utf-8:utf-8"

WORKDIR /opt/kathara/scripts/Linux-Arch
