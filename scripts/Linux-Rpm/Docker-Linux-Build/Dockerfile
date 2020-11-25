FROM fedora:32

RUN dnf install -y rubygem-rails ruby-devel zlib-devel make \
		   python3-devel python3-pip \
		   @development-tools fedora-packager rpmdevtools

RUN dnf remove -y python3-pyroute2

RUN gem install ronn-ng

RUN rpmdev-setuptree

ENV RUBYOPT="-KU -E utf-8:utf-8"

WORKDIR /opt/kathara/scripts/Linux-Rpm
