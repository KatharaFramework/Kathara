FROM archlinux:latest

ENV RUBYOPT="-KU -E utf-8:utf-8"

RUN pacman -Syyu --noconfirm
RUN pacman-db-upgrade

RUN pacman -S --noconfirm git \
			  			  openssh \
			  			  base-devel \
			  			  chrpath \
                          patchelf \
    					  ruby-ronn-ng \
                          python
                          
RUN useradd -m -s /bin/bash builduser

RUN su -c "mkdir -p /home/builduser/build/" builduser

WORKDIR /home/builduser/build/
