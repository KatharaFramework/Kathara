FROM archlinux:latest

ENV RUBYOPT="-KU -E utf-8:utf-8"

RUN pacman -Syyu --noconfirm
RUN pacman-db-upgrade

RUN pacman -S --noconfirm git \
			  			  openssh \
			  			  base-devel \
			  			  chrpath \
                          patchelf \
    					  ruby-ronn-ng
                          
RUN pacman -S --noconfirm wget && \
    wget https://archive.archlinux.org/packages/p/python/python-3.10.10-1-x86_64.pkg.tar.zst && \
    pacman -U --noconfirm python-3.10.10-1-x86_64.pkg.tar.zst && \
    rm -f python-3.10.10-1-x86_64.pkg.tar.zst
                          
RUN useradd -m -s /bin/bash builduser

RUN su -c "mkdir -p /home/builduser/build/" builduser

WORKDIR /home/builduser/build/
