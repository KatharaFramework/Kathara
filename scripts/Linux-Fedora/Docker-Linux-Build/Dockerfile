FROM fedora

RUN yum install -y python3 \
		   python3-devel \
		   python3-pip \
		   python3-setuptools \
		   git \
		   bash-completion \
		   which

RUN dnf install -y gcc-c++ patch readline readline-devel zlib zlib-devel \
    		   libyaml-devel libffi-devel openssl-devel make \
    		   bzip2 autoconf automake libtool bison sqlite-devel procps \
    		   @development-tools fedora-packager rpmdevtools
    		
RUN git clone https://github.com/rbenv/ruby-build.git && \
  		PREFIX=/usr/local ./ruby-build/install.sh && \
  		ruby-build -v 2.4.1 /usr/local && \
  		gem install ronn-ng

WORKDIR /opt/kathara/scripts/Linux-Fedora
