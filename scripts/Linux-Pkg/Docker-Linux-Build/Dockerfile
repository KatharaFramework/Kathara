FROM archlinux:base-20210131.0.14634

RUN pacman -Syyu --noconfirm
RUN pacman-db-upgrade

RUN useradd -m -s /bin/bash builduser 

RUN pacman -S --noconfirm git \
			  			  openssh \
				 		  base-devel \
				 		  python-pip \
				 		  ruby 

RUN su -c "gem install ronn-ng" builduser

ENV RUBYOPT="-KU -E utf-8:utf-8"

RUN echo "IdentityFile /home/builduser/.ssh/id_rsa" >> /etc/ssh/ssh_config

WORKDIR /opt/kathara/scripts/Linux-Pkg
