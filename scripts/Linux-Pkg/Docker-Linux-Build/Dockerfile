FROM archlinux:base-20210131.0.14634

ENV RUBYOPT="-KU -E utf-8:utf-8"

RUN pacman -Syyu --noconfirm
RUN pacman-db-upgrade

RUN pacman -S --noconfirm git \
			  			  openssh \
			  			  base-devel \
			  			  ruby \
			  			  chrpath \
                          patchelf
                          
RUN pacman -S --noconfirm wget \
						  bzip2 \
						  expat \
						  gdbm \
						  libffi \
						  libnsl \
						  libxcrypt \
						  openssl \
						  zlib && \
	wget https://www.python.org/ftp/python/3.9.9/Python-3.9.9.tgz && \
	tar xfvz Python-3.9.9.tgz && cd Python-3.9.9 && \
	./configure --enable-optimizations && \
	make -j8 && \
	make install && \
	pacman -R --noconfirm wget && \
    cd .. && rm -Rf Python-3.9.9*
                          
RUN useradd -m -s /bin/bash builduser

RUN su -c "gem install ronn-ng" builduser

RUN echo "IdentityFile /home/builduser/.ssh/id_rsa" >> /etc/ssh/ssh_config

WORKDIR /opt/kathara/scripts/Linux-Pkg
