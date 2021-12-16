FROM archlinux:base-20210131.0.14634

ENV RUBYOPT="-KU -E utf-8:utf-8"

RUN pacman -Syyu --noconfirm
RUN pacman-db-upgrade

RUN echo "[community]\nInclude = /etc/pacman.d/mirrorlist\n" >> /etc/pacman.conf

RUN pacman -S --noconfirm git \
			  			  openssh \
				 		  base-devel \
				 		  python-pip \
				 		  ruby \
						  chrpath \
                          patchelf

RUN useradd -m -s /bin/bash builduser

RUN su -c "gem install ronn-ng" builduser

RUN echo "IdentityFile /home/builduser/.ssh/id_rsa" >> /etc/ssh/ssh_config

WORKDIR /opt/kathara/scripts/Linux-Pkg
