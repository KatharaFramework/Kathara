FROM fedora:32

RUN dnf install -y gcc-c++ patch readline readline-devel zlib zlib-devel \
    		       libyaml-devel libffi-devel openssl-devel make \
    		       bzip2 autoconf automake libtool bison sqlite-devel procps wget \
    		       git bash-completion which python3-devel python3-pip \
    		       @development-tools fedora-packager rpmdevtools

RUN dnf remove -y python3-pyroute2

RUN git clone https://github.com/rbenv/ruby-build.git && \
  		PREFIX=/usr/local ./ruby-build/install.sh && \
  		ruby-build -v 2.4.1 /usr/local && \
  		rm -Rf ./ruby-build && \
  		gem install ronn-ng

RUN rpmdev-setuptree

ENV RUBYOPT="-KU -E utf-8:utf-8"

WORKDIR /opt/kathara/scripts/Linux-Rpm
